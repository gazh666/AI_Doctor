from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import or_, select, text

from app.core.config import settings
from app.db.models import MedicalDocument
from app.db.session import AsyncSessionLocal


def _trim_excerpt(text: str, max_len: int = 420) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[:max_len].rstrip() + "..."


async def _embed_query(query: str) -> list[float] | None:
    if not settings.GOOGLE_API_KEY:
        return None

    def _call_embed() -> list[float] | None:
        try:
            import google.generativeai as genai
        except Exception:
            return None
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        result = genai.embed_content(
            model=settings.EMBEDDING_MODEL,
            content=query,
            task_type="retrieval_query",
        )
        embedding = result.get("embedding") if isinstance(result, dict) else None
        return embedding if isinstance(embedding, list) else None

    try:
        return await asyncio.to_thread(_call_embed)
    except Exception:
        return None


async def _metadata_column_exists(db: Any) -> bool:
        exists_stmt = text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'medical_documents'
                    AND column_name = 'metadata'
                LIMIT 1
                """
        )
        result = await db.execute(exists_stmt)
        return result.scalar_one_or_none() == 1


async def retrieve_medical_grounding(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Return grounded source citations from MedicalDocument with vector-first retrieval.

    Falls back to lexical matching when embeddings/vector query is unavailable.
    """
    citations: list[dict[str, Any]] = []
    embedding = await _embed_query(query)

    async with AsyncSessionLocal() as db:
        rows = []
        has_metadata_column = await _metadata_column_exists(db)

        select_columns = [
            MedicalDocument.id,
            MedicalDocument.title,
            MedicalDocument.content,
        ]
        if has_metadata_column:
            select_columns.append(MedicalDocument.metadata_json)

        if embedding:
            try:
                vector_stmt = (
                    select(
                        *select_columns,
                        (1 - MedicalDocument.embedding.cosine_distance(embedding)).label("similarity"),
                    )
                    .where(MedicalDocument.embedding.is_not(None))
                    .order_by(MedicalDocument.embedding.cosine_distance(embedding))
                    .limit(top_k)
                )
                vector_result = await db.execute(vector_stmt)
                rows = list(vector_result.all())
            except Exception:
                rows = []

        if not rows:
            lexical_stmt = (
                select(*select_columns)
                .where(
                    or_(
                        MedicalDocument.title.ilike(f"%{query}%"),
                        MedicalDocument.content.ilike(f"%{query}%"),
                    )
                )
                .limit(top_k)
            )
            lexical_result = await db.execute(lexical_stmt)
            rows = list(lexical_result.all())

        for idx, row in enumerate(rows, start=1):
            metadata = row.metadata_json if has_metadata_column and hasattr(row, "metadata_json") else None
            source_ref = ""
            if isinstance(metadata, dict):
                source_ref = str(metadata.get("source") or metadata.get("file") or "")

            content = row.content if hasattr(row, "content") else ""
            excerpt = _trim_excerpt(content or "No excerpt available")
            citations.append(
                {
                    "id": int(row.id),
                    "rank": idx,
                    "provider": "LocalRAG",
                    "title": row.title or f"Medical Source #{idx}",
                    "source": source_ref,
                    "excerpt": excerpt,
                    "similarity": float(getattr(row, "similarity", 0.0) or 0.0),
                }
            )

    return citations
