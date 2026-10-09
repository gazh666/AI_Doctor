from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select

from app.core.config import settings
from app.db.models import MedicalEvidenceSource
from app.db.session import AsyncSessionLocal


def _trim_excerpt(text: str, max_len: int = 420) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[:max_len].rstrip() + "..."


def _provider_weight(provider: str) -> float:
    weights = {
        "WHO": 1.0,
        "CDC": 0.98,
        "NICE": 0.97,
        "PubMed": 0.95,
        "OpenFDA": 0.92,
        "MedlinePlus": 0.9,
        "ClinicalTrials": 0.86,
        "LocalRAG": 0.84,
    }
    return weights.get(provider, 0.8)


def _evidence_level_weight(level: str | None) -> float:
    weights = {
        "guideline": 1.0,
        "systematic_review": 0.98,
        "rct": 0.95,
        "meta_analysis": 0.95,
        "observational": 0.85,
        "expert_consensus": 0.8,
        "reference": 0.75,
    }
    if not level:
        return 0.75
    return weights.get(level.strip().lower(), 0.75)


async def embed_text(text: str, task_type: str = "retrieval_document") -> list[float] | None:
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
            content=text,
            task_type=task_type,
        )
        embedding = result.get("embedding") if isinstance(result, dict) else None
        return embedding if isinstance(embedding, list) else None

    try:
        return await asyncio.to_thread(_call_embed)
    except Exception:
        return None


async def retrieve_catalog_citations(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    """Retrieve references from curated, database-backed medical evidence sources."""
    citations: list[dict[str, Any]] = []
    query_embedding = await embed_text(query, task_type="retrieval_query")

    async with AsyncSessionLocal() as db:
        rows = []
        if query_embedding:
            try:
                vector_stmt = (
                    select(
                        MedicalEvidenceSource,
                        (1 - MedicalEvidenceSource.embedding.cosine_distance(query_embedding)).label("similarity"),
                    )
                    .where(
                        MedicalEvidenceSource.is_active.is_(True),
                        MedicalEvidenceSource.embedding.is_not(None),
                    )
                    .order_by(MedicalEvidenceSource.embedding.cosine_distance(query_embedding))
                    .limit(top_k)
                )
                vector_result = await db.execute(vector_stmt)
                rows = list(vector_result.all())
            except Exception:
                rows = []

        if not rows:
            lexical_stmt = (
                select(MedicalEvidenceSource)
                .where(
                    MedicalEvidenceSource.is_active.is_(True),
                    or_(
                        MedicalEvidenceSource.title.ilike(f"%{query}%"),
                        MedicalEvidenceSource.excerpt.ilike(f"%{query}%"),
                    ),
                )
                .limit(top_k)
            )
            lexical_result = await db.execute(lexical_stmt)
            rows = [(item, 0.0) for item in lexical_result.scalars().all()]

        for rank, (source, similarity) in enumerate(rows, start=1):
            provider = str(source.provider or "Catalog")
            weighted_similarity = float(similarity or 0.0) * _provider_weight(provider) * _evidence_level_weight(source.evidence_level)
            citations.append(
                {
                    "id": int(source.id),
                    "rank": rank,
                    "provider": provider,
                    "title": source.title,
                    "source": source.url,
                    "excerpt": _trim_excerpt(source.excerpt),
                    "similarity": weighted_similarity,
                    "evidence_level": source.evidence_level,
                    "published_at": source.published_at.isoformat() if source.published_at else None,
                    "last_verified_at": source.last_verified_at.isoformat() if source.last_verified_at else None,
                }
            )

    citations.sort(key=lambda c: float(c.get("similarity", 0.0)), reverse=True)
    for idx, citation in enumerate(citations, start=1):
        citation["rank"] = idx
    return citations[: max(1, top_k)]


def default_trusted_sources() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return [
        {
            "provider": "NICE",
            "title": "Fever in under 5s: assessment and initial management (NG143)",
            "url": "https://www.nice.org.uk/guidance/ng143",
            "excerpt": "Children with any high-risk red features should be urgently referred for emergency medical care. Use traffic-light risk stratification to guide assessment and management.",
            "condition_tags": ["fever", "pediatrics", "triage", "emergency-referral", "ng143"],
            "evidence_level": "guideline",
            "last_verified_at": now,
        },
        {
            "provider": "CDC",
            "title": "Clinical Guidance for Group A Streptococcal Pharyngitis",
            "url": "https://www.cdc.gov/group-a-strep/hcp/clinical-guidance/strep-throat.html",
            "excerpt": "In symptomatic children aged 3 years or older, confirm a negative rapid antigen test with throat culture. Treat confirmed group A strep pharyngitis with penicillin or amoxicillin.",
            "condition_tags": ["sore-throat", "pediatrics", "diagnosis", "antibiotics", "gas-pharyngitis"],
            "evidence_level": "guideline",
            "last_verified_at": now,
        },
        {
            "provider": "NICE",
            "title": "Bronchiolitis in children: diagnosis and management (NG9)",
            "url": "https://www.nice.org.uk/guidance/ng9/chapter/recommendations",
            "excerpt": "Do not use antibiotics, salbutamol, adrenaline, montelukast, ipratropium bromide, or corticosteroids to treat bronchiolitis in children.",
            "condition_tags": ["bronchiolitis", "infants", "respiratory", "supportive-care", "ng9"],
            "evidence_level": "guideline",
            "last_verified_at": now,
        },
        {
            "provider": "NICE",
            "title": "Urinary tract infection in under 16s: diagnosis and management (NG224)",
            "url": "https://www.nice.org.uk/guidance/ng224/chapter/Recommendations",
            "excerpt": "Test urine in children when symptoms and signs increase the likelihood of urinary tract infection, including non-specific illness in younger children.",
            "condition_tags": ["uti", "pediatrics", "diagnosis", "urine-testing", "ng224"],
            "evidence_level": "guideline",
            "last_verified_at": now,
        },
        {
            "provider": "CDC",
            "title": "Outpatient Clinical Care for Pediatric Populations",
            "url": "https://www.cdc.gov/antibiotic-use/hcp/clinical-care/pediatric-outpatient.html",
            "excerpt": "For bronchiolitis, routine use of antibiotics and bronchodilators is not recommended in children without evidence of bacterial coinfection.",
            "condition_tags": ["bronchiolitis", "pediatrics", "antibiotic-stewardship", "outpatient"],
            "evidence_level": "guideline",
            "last_verified_at": now,
        },
        {
            "provider": "WHO",
            "title": "Oral rehydration salts (WHO-FCH-CAH-06.1)",
            "url": "https://www.who.int/publications/i/item/WHO-FCH-CAH-06.1",
            "excerpt": "Diarrhoea-related dehydration can be treated effectively in most children using oral rehydration salts with ongoing fluid replacement.",
            "condition_tags": ["diarrhea", "dehydration", "pediatrics", "ors", "community-care"],
            "evidence_level": "guideline",
            "last_verified_at": now,
        },
        {
            "provider": "WHO",
            "title": "Zinc supplementation in the management of diarrhoea",
            "url": "https://www.who.int/tools/elena/interventions/zinc-diarrhoea",
            "excerpt": "In acute childhood diarrhoea, give zinc for 10 to 14 days: 20 mg daily for children older than 6 months and 10 mg daily for infants younger than 6 months.",
            "condition_tags": ["diarrhea", "children", "zinc", "treatment", "who-elena"],
            "evidence_level": "guideline",
            "last_verified_at": now,
        },
        {
            "provider": "PubMed",
            "title": "Delayed antibiotic prescribing for respiratory tract infections (PMID: 33910882)",
            "url": "https://pubmed.ncbi.nlm.nih.gov/33910882/",
            "excerpt": "Individual patient data meta-analysis found delayed prescribing achieved similar symptom control to immediate antibiotics for many respiratory tract infections while reducing antibiotic use.",
            "condition_tags": ["respiratory-infection", "antibiotic-stewardship", "delayed-prescription", "systematic-review"],
            "evidence_level": "systematic_review",
            "last_verified_at": now,
        },
        {
            "provider": "PubMed",
            "title": "Single-dose oral dexamethasone for mild croup (PMID: 15385657)",
            "url": "https://pubmed.ncbi.nlm.nih.gov/15385657/",
            "excerpt": "Randomized trial evidence showed single-dose oral dexamethasone improved short-term outcomes and reduced return visits in children with mild croup.",
            "condition_tags": ["croup", "pediatrics", "dexamethasone", "emergency-care", "rct"],
            "evidence_level": "rct",
            "last_verified_at": now,
        },
        {
            "provider": "OpenFDA",
            "title": "Drug Labeling API boxed warning query pattern",
            "url": "https://open.fda.gov/apis/drug/label/example-api-queries/",
            "excerpt": "Use the _exists_:boxed_warning search pattern in OpenFDA drug labels to retrieve records with high-risk safety warnings for downstream triage checks.",
            "condition_tags": ["medication-safety", "boxed-warning", "contraindication", "pharmacovigilance"],
            "evidence_level": "reference",
            "last_verified_at": now,
        },
    ]
