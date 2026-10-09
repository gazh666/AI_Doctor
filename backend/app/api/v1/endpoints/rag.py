import asyncio
import csv
import io
import re
import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_active_user, get_current_admin_user
from app.db.models import MedicalDocument, MedicalEvidenceSource, User
from app.db.session import get_db
from app.schemas.rag import (
    RagCitation,
    RagQueryRequest,
    RagQueryResponse,
    RagUploadResponse,
    TrustedSourceCreateRequest,
    TrustedSourceResponse,
    TrustedSourceSeedResponse,
)
from app.services.llm.gemini_client import gemini_client
from app.services.rag.reputable_sources import retrieve_reputable_citations
from app.services.rag.source_catalog import default_trusted_sources, embed_text, retrieve_catalog_citations


router = APIRouter()

MAX_UPLOAD_BYTES = 40 * 1024 * 1024
FALLBACK_EMBEDDING = [0.0] * 768
LOCAL_RELEVANCE_THRESHOLD = 0.2


def _chunk_text(text: str, chunk_size: int = 2500, overlap: int = 250) -> List[str]:
    text = " ".join(text.split())
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        if end >= text_len:
            break
        start = max(0, end - overlap)
    return chunks


def _extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text: List[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages_text.append(page_text)
    return "\n\n".join(pages_text).strip()


def _extract_txt_text(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore").strip()


def _extract_csv_text(file_bytes: bytes) -> str:
    decoded = file_bytes.decode("utf-8", errors="ignore")
    reader = csv.reader(io.StringIO(decoded))
    rows: list[str] = []
    for row in reader:
        cleaned_cells = [cell.strip() for cell in row if cell and cell.strip()]
        if cleaned_cells:
            rows.append(" | ".join(cleaned_cells))
    return "\n".join(rows).strip()


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}


def _score_chunk(question: str, content: str) -> float:
    q_terms = _tokenize(question)
    if not q_terms:
        return 0.0
    c_terms = _tokenize(content)
    overlap = len(q_terms & c_terms)
    phrase_bonus = 1.0 if question.lower() in content.lower() else 0.0
    return (overlap / len(q_terms)) + phrase_bonus


def _provider_weight(provider: str) -> float:
    weights = {
        "LocalRAG": 1.0,
        "PubMed": 0.95,
        "OpenFDA": 0.9,
        "MedlinePlus": 0.85,
        "ClinicalTrials": 0.8,
    }
    return weights.get(provider, 0.75)


def _rank_citation_dicts(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        citations,
        key=lambda c: float(c.get("similarity", 0.0) or 0.0) * _provider_weight(str(c.get("provider") or "")),
        reverse=True,
    )
    for idx, citation in enumerate(ranked, start=1):
        citation["rank"] = idx
    return ranked


async def _embed_text(text: str) -> list[float]:
    if not settings.GOOGLE_API_KEY:
        return FALLBACK_EMBEDDING

    def _call_embed() -> list[float]:
        try:
            import google.generativeai as genai
        except Exception:
            return FALLBACK_EMBEDDING
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        result = genai.embed_content(
            model=settings.EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_document",
        )
        embedding = result.get("embedding") if isinstance(result, dict) else None
        if isinstance(embedding, list) and len(embedding) == 768:
            return [float(v) for v in embedding]
        return FALLBACK_EMBEDDING

    try:
        return await asyncio.to_thread(_call_embed)
    except Exception:
        return FALLBACK_EMBEDDING


@router.post(
    "/upload-pdf",
    response_model=RagUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload PDF, TXT, MD, or CSV to personal RAG knowledge base",
)
async def upload_pdf_to_rag(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    lower_name = file.filename.lower()
    is_pdf = lower_name.endswith(".pdf")
    is_txt = lower_name.endswith(".txt")
    is_md = lower_name.endswith(".md")
    is_csv = lower_name.endswith(".csv")
    if not (is_pdf or is_txt or is_md or is_csv):
        raise HTTPException(status_code=400, detail="Only PDF, TXT, MD, and CSV files are supported")

    file_bytes = await file.read()
    size_bytes = len(file_bytes)
    if size_bytes > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 40MB size limit",
        )

    try:
        if is_pdf:
            extracted_text = _extract_pdf_text(file_bytes)
        elif is_csv:
            extracted_text = _extract_csv_text(file_bytes)
        else:
            extracted_text = _extract_txt_text(file_bytes)
    except Exception as exc:
        file_type = "PDF" if is_pdf else "CSV" if is_csv else "TEXT"
        raise HTTPException(status_code=400, detail=f"Failed to read {file_type}: {exc}") from exc

    if not extracted_text:
        raise HTTPException(status_code=400, detail="File contains no extractable text")

    chunks = _chunk_text(extracted_text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No usable text chunks were produced")

    max_chunks = max(1, settings.RAG_MAX_CHUNKS_PER_DOC)
    truncated = len(chunks) > max_chunks
    if truncated:
        chunks = chunks[:max_chunks]

    kb_id = str(uuid.uuid4())
    created_rows: list[MedicalDocument] = []

    for idx, chunk in enumerate(chunks, start=1):
        embedding = await _embed_text(chunk)
        created_rows.append(
            MedicalDocument(
                title=f"{file.filename} (part {idx}/{len(chunks)})",
                content=chunk,
                embedding=embedding,
                metadata_json={
                    "source": file.filename,
                    "knowledge_base_id": kb_id,
                    "uploader_user_id": current_user.id,
                    "chunk_index": idx,
                    "chunk_total": len(chunks),
                },
            )
        )

    db.add_all(created_rows)
    await db.commit()

    return RagUploadResponse(
        knowledge_base_id=kb_id,
        filename=file.filename,
        size_bytes=size_bytes,
        chunks_indexed=len(chunks),
        truncated=truncated,
        message="File indexed successfully and ready for Q&A",
    )


@router.post(
    "/query",
    response_model=RagQueryResponse,
    summary="Ask questions over uploaded personal reports",
)
async def query_uploaded_reports(
    request: RagQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = select(
        MedicalDocument.id,
        MedicalDocument.title,
        MedicalDocument.content,
        MedicalDocument.metadata_json,
    ).where(
        cast(MedicalDocument.metadata_json["uploader_user_id"], String) == str(current_user.id)
    )

    result = await db.execute(stmt)
    rows = list(result.all())

    local_citation_dicts: list[dict[str, Any]] = []
    if rows:
        scored_rows: list[tuple[Any, float]] = [
            (row, _score_chunk(request.question, row.content or "")) for row in rows
        ]
        scored_rows.sort(key=lambda item: item[1], reverse=True)

        relevant_rows = [pair for pair in scored_rows if pair[1] >= LOCAL_RELEVANCE_THRESHOLD]
        selected_rows = relevant_rows[: request.top_k]

        for row, score in selected_rows:
            metadata: Any = row.metadata_json if hasattr(row, "metadata_json") else {}
            source = ""
            if isinstance(metadata, dict):
                source = str(metadata.get("source") or "")

            local_citation_dicts.append(
                {
                    "id": int(row.id),
                    "rank": 0,
                    "provider": "LocalRAG",
                    "title": row.title or "Uploaded Report Chunk",
                    "source": source,
                    "excerpt": (row.content or "")[:700],
                    "similarity": float(score),
                    "content": row.content or "",
                }
            )

    catalog_citation_dicts: list[dict[str, Any]] = []
    reputable_citation_dicts: list[dict[str, Any]] = []
    try:
        catalog_citation_dicts, reputable_citation_dicts = await asyncio.gather(
            retrieve_catalog_citations(request.question, top_k=min(3, request.top_k)),
            retrieve_reputable_citations(
                request.question,
                top_k=min(2, request.top_k),
            ),
        )
    except Exception:
        catalog_citation_dicts = []
        reputable_citation_dicts = []

    merged_ranked = _rank_citation_dicts([
        *local_citation_dicts,
        *catalog_citation_dicts,
        *reputable_citation_dicts,
    ])[: request.top_k]

    citations: list[RagCitation] = []
    context_blocks: list[str] = []
    has_local_context = False

    for citation in merged_ranked:
        rank = int(citation.get("rank", 0) or 0)
        citation_id = int(citation.get("id", rank) or rank)
        title = str(citation.get("title") or f"Source {rank}")
        source = str(citation.get("source") or "")
        excerpt = str(citation.get("excerpt") or "")
        provider = str(citation.get("provider") or "")

        citations.append(
            RagCitation(
                id=citation_id,
                rank=rank,
                title=title,
                source=source,
                excerpt=excerpt,
                provider=provider,
                similarity=float(citation.get("similarity", 0.0) or 0.0),
                evidence_level=citation.get("evidence_level"),
                published_at=citation.get("published_at"),
                last_verified_at=citation.get("last_verified_at"),
            )
        )

        if provider == "LocalRAG":
            has_local_context = True
            content = str(citation.get("content") or excerpt)
            context_blocks.append(f"[{rank}] {title}\n{content}")
        else:
            context_blocks.append(f"[{rank}] {title}\n{excerpt}")

    context_text = "\n\n".join(context_blocks)

    if context_blocks:
        prompt = (
            "You are a medical assistant. Use provided context first. "
            "If context is incomplete, then use reliable general medical knowledge and say that part is general guidance. "
            "Use citations like [1], [2] only for claims supported by the provided context blocks.\n\n"
            f"Question:\n{request.question}\n\n"
            f"Context:\n{context_text}"
        )
    else:
        prompt = (
            "You are a medical assistant. No relevant uploaded context is available. "
            "Answer from general medical knowledge in a clear, practical way with safety caveats. "
            "If urgent warning signs exist, advise immediate care.\n\n"
            f"Question:\n{request.question}"
        )

    try:
        answer = await gemini_client.generate(prompt)
    except Exception:
        answer = (
            "I could not generate a model answer right now. "
            "Based on your uploaded report, please review the cited excerpts."
        )

    if not has_local_context and not citations:
        citations = []

    return RagQueryResponse(answer=str(answer), matched_chunks=len(citations), citations=citations)


@router.post(
    "/sources",
    response_model=TrustedSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add curated medical reference source (admin only)",
)
async def create_trusted_source(
    request: TrustedSourceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    del current_admin

    source_text = f"{request.title}\n{request.excerpt}\nTags: {', '.join(request.condition_tags)}"
    embedding = await embed_text(source_text, task_type="retrieval_document")

    row = MedicalEvidenceSource(
        provider=request.provider.strip(),
        title=request.title.strip(),
        url=str(request.url),
        excerpt=request.excerpt.strip(),
        condition_tags=request.condition_tags,
        evidence_level=request.evidence_level,
        published_at=request.published_at,
        last_verified_at=request.last_verified_at,
        embedding=embedding,
        metadata_json=request.metadata,
        is_active=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return TrustedSourceResponse(
        id=row.id,
        provider=row.provider,
        title=row.title,
        url=row.url,
        excerpt=row.excerpt,
        condition_tags=row.condition_tags or [],
        evidence_level=row.evidence_level,
        published_at=row.published_at.isoformat() if row.published_at else None,
        last_verified_at=row.last_verified_at.isoformat() if row.last_verified_at else None,
        is_active=bool(row.is_active),
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get(
    "/sources",
    response_model=List[TrustedSourceResponse],
    summary="List curated medical reference sources",
)
async def list_trusted_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    del current_user
    result = await db.execute(
        select(MedicalEvidenceSource)
        .where(MedicalEvidenceSource.is_active.is_(True))
        .order_by(MedicalEvidenceSource.provider.asc(), MedicalEvidenceSource.id.asc())
    )
    rows = result.scalars().all()
    return [
        TrustedSourceResponse(
            id=row.id,
            provider=row.provider,
            title=row.title,
            url=row.url,
            excerpt=row.excerpt,
            condition_tags=row.condition_tags or [],
            evidence_level=row.evidence_level,
            published_at=row.published_at.isoformat() if row.published_at else None,
            last_verified_at=row.last_verified_at.isoformat() if row.last_verified_at else None,
            is_active=bool(row.is_active),
            created_at=row.created_at.isoformat() if row.created_at else None,
        )
        for row in rows
    ]


@router.post(
    "/sources/seed-defaults",
    response_model=TrustedSourceSeedResponse,
    summary="Seed trusted baseline references (admin only)",
)
async def seed_default_trusted_sources(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    del current_admin

    defaults = default_trusted_sources()
    inserted = 0
    skipped = 0
    for item in defaults:
        existing = await db.execute(
            select(MedicalEvidenceSource.id).where(
                MedicalEvidenceSource.provider == item["provider"],
                MedicalEvidenceSource.title == item["title"],
            )
        )
        if existing.scalar_one_or_none() is not None:
            skipped += 1
            continue

        source_text = f"{item['title']}\n{item['excerpt']}\nTags: {', '.join(item.get('condition_tags', []))}"
        embedding = await embed_text(source_text, task_type="retrieval_document")
        db.add(
            MedicalEvidenceSource(
                provider=item["provider"],
                title=item["title"],
                url=item["url"],
                excerpt=item["excerpt"],
                condition_tags=item.get("condition_tags", []),
                evidence_level=item.get("evidence_level"),
                published_at=item.get("published_at"),
                last_verified_at=item.get("last_verified_at") or item.get("published_at"),
                embedding=embedding,
                metadata_json={"seeded": True},
                is_active=True,
            )
        )
        inserted += 1

    await db.commit()
    return TrustedSourceSeedResponse(inserted=inserted, skipped_existing=skipped)
