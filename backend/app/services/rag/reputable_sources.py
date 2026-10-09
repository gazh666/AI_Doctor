from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.config import settings

PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
MEDLINEPLUS_CONNECT_URL = "https://connect.medlineplus.gov/service"
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
CLINICAL_TRIALS_V2_URL = "https://clinicaltrials.gov/api/v2/studies"


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_rank(citations: list[dict[str, Any]], start: int = 1) -> list[dict[str, Any]]:
    rank = start
    for citation in citations:
        citation["rank"] = rank
        rank += 1
    return citations


def _provider_weight(provider: str) -> float:
    weights = {
        "PubMed": 1.0,
        "OpenFDA": 0.95,
        "MedlinePlus": 0.9,
        "ClinicalTrials": 0.85,
    }
    return weights.get(provider, 0.8)


def _rank_reputable_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        citations,
        key=lambda c: float(c.get("similarity", 0.0) or 0.0) * _provider_weight(str(c.get("provider") or "")),
        reverse=True,
    )
    return _normalize_rank(ranked)


def _build_source_id(prefix: int, raw_id: str | int, fallback: int) -> int:
    try:
        return prefix + int(raw_id)
    except Exception:
        return prefix + fallback


async def retrieve_medlineplus_citations(query: str, top_k: int = 2) -> list[dict[str, Any]]:
    """Fetch patient-facing trusted references from MedlinePlus Connect."""
    params = {
        "mainSearchCriteria.v.dn": query,
        "informationRecipient.languageCode.c": "en",
        "knowledgeResponseType": "application/json",
    }

    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            response = await client.get(MEDLINEPLUS_CONNECT_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

    entries = data.get("feed", {}).get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]

    citations: list[dict[str, Any]] = []
    for idx, entry in enumerate(entries[: max(1, top_k)], start=1):
        title = _safe_text((entry.get("title") or {}).get("_value")) or "MedlinePlus Topic"
        summary = _safe_text((entry.get("summary") or {}).get("_value"))
        links = entry.get("link") or []
        if isinstance(links, dict):
            links = [links]
        source_url = "https://medlineplus.gov"
        for link in links:
            href = _safe_text(link.get("href"))
            if href:
                source_url = href
                break

        citations.append(
            {
                "id": _build_source_id(2_000_000_000, idx, idx),
                "rank": idx,
                "provider": "MedlinePlus",
                "title": f"[MedlinePlus] {title}",
                "source": source_url,
                "excerpt": summary or "Patient-friendly medical overview from MedlinePlus.",
                "similarity": 0.7,
            }
        )

    return citations


async def retrieve_pubmed_citations(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Fetch diagnosis-supporting citations from PubMed (NCBI E-utilities).

    This is best-effort only: failures should never break diagnosis flow.
    """
    search_term = f"{query} diagnosis guideline"
    esearch_params = {
        "db": "pubmed",
        "retmode": "json",
        "retmax": str(max(1, top_k)),
        "sort": "relevance",
        "term": search_term,
    }
    if settings.NCBI_API_KEY:
        esearch_params["api_key"] = settings.NCBI_API_KEY

    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            search_response = await client.get(
                PUBMED_ESEARCH_URL,
                params=esearch_params,
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            esummary_params = {
                "db": "pubmed",
                "retmode": "json",
                "id": ",".join(id_list),
            }
            if settings.NCBI_API_KEY:
                esummary_params["api_key"] = settings.NCBI_API_KEY

            summary_response = await client.get(
                PUBMED_ESUMMARY_URL,
                params=esummary_params,
            )
            summary_response.raise_for_status()
            summary_data = summary_response.json().get("result", {})
        except Exception:
            return []

    citations: list[dict[str, Any]] = []
    rank = 1
    for pmid in id_list:
        item = summary_data.get(str(pmid), {})
        if not isinstance(item, dict):
            continue

        title = str(item.get("title") or "Untitled PubMed Article").strip()
        journal = str(item.get("fulljournalname") or item.get("source") or "PubMed").strip()
        pubdate = str(item.get("pubdate") or "Unknown date").strip()
        authors = item.get("authors") or []
        first_author = ""
        if isinstance(authors, list) and authors:
            first = authors[0]
            if isinstance(first, dict):
                first_author = str(first.get("name") or "").strip()

        excerpt_parts = [f"Journal: {journal}", f"Published: {pubdate}"]
        if first_author:
            excerpt_parts.append(f"Lead Author: {first_author}")

        citations.append(
            {
                "id": 1_000_000_000 + int(pmid),
                "rank": rank,
                "provider": "PubMed",
                "title": f"[PubMed] {title}",
                "source": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "excerpt": " | ".join(excerpt_parts),
                "similarity": 0.75,
            }
        )
        rank += 1

    return citations


async def retrieve_openfda_citations(query: str, top_k: int = 2) -> list[dict[str, Any]]:
    """Fetch FDA label evidence for treatment and warning references."""
    search_expr = f"openfda.brand_name:{query}"

    params = {
        "search": search_expr,
        "limit": str(max(1, top_k)),
    }
    if settings.OPENFDA_API_KEY:
        params["api_key"] = settings.OPENFDA_API_KEY

    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            response = await client.get(OPENFDA_LABEL_URL, params=params)
            if response.status_code >= 400:
                response = await client.get(
                    OPENFDA_LABEL_URL,
                    params={
                        "search": f"indications_and_usage:{query}",
                        "limit": str(max(1, top_k)),
                        **({"api_key": settings.OPENFDA_API_KEY} if settings.OPENFDA_API_KEY else {}),
                    },
                )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

    results = data.get("results") or []
    citations: list[dict[str, Any]] = []

    for idx, item in enumerate(results[: max(1, top_k)], start=1):
        openfda = item.get("openfda") or {}
        brand_name = ""
        if isinstance(openfda, dict):
            brands = openfda.get("brand_name") or []
            if isinstance(brands, list) and brands:
                brand_name = _safe_text(brands[0])

        indications = item.get("indications_and_usage") or []
        warnings = item.get("warnings") or []
        indication_text = _safe_text(indications[0] if isinstance(indications, list) and indications else "")
        warning_text = _safe_text(warnings[0] if isinstance(warnings, list) and warnings else "")

        excerpt = indication_text or warning_text or "FDA label entry available."
        if len(excerpt) > 420:
            excerpt = excerpt[:420].rstrip() + "..."

        citations.append(
            {
                "id": _build_source_id(3_000_000_000, idx, idx),
                "rank": idx,
                "provider": "OpenFDA",
                "title": f"[OpenFDA] {brand_name or 'Drug Label'}",
                "source": "https://open.fda.gov/apis/drug/label/",
                "excerpt": excerpt,
                "similarity": 0.72,
            }
        )

    return citations


async def retrieve_clinicaltrials_citations(query: str, top_k: int = 2) -> list[dict[str, Any]]:
    """Fetch relevant study summaries from ClinicalTrials.gov v2 API."""
    params = {
        "query.term": query,
        "pageSize": str(max(1, top_k)),
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            response = await client.get(CLINICAL_TRIALS_V2_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

    studies = data.get("studies") or []
    citations: list[dict[str, Any]] = []

    for idx, study in enumerate(studies[: max(1, top_k)], start=1):
        protocol = study.get("protocolSection") or {}
        ident = protocol.get("identificationModule") or {}
        status = protocol.get("statusModule") or {}
        conditions = protocol.get("conditionsModule") or {}

        nct_id = _safe_text(ident.get("nctId"))
        title = _safe_text(ident.get("briefTitle")) or "Clinical Study"
        overall_status = _safe_text(status.get("overallStatus")) or "Status not reported"
        condition_list = conditions.get("conditions") or []
        top_condition = _safe_text(condition_list[0] if isinstance(condition_list, list) and condition_list else "")

        excerpt_parts = [f"Status: {overall_status}"]
        if top_condition:
            excerpt_parts.append(f"Condition: {top_condition}")

        source_url = "https://clinicaltrials.gov"
        if nct_id:
            source_url = f"https://clinicaltrials.gov/study/{nct_id}"

        citations.append(
            {
                "id": _build_source_id(4_000_000_000, nct_id or idx, idx),
                "rank": idx,
                "provider": "ClinicalTrials",
                "title": f"[ClinicalTrials] {title}",
                "source": source_url,
                "excerpt": " | ".join(excerpt_parts),
                "similarity": 0.68,
            }
        )

    return citations


async def retrieve_reputable_citations(query: str, top_k: int = 6) -> list[dict[str, Any]]:
    """Aggregate reputable healthcare sources for diagnosis-time citations."""
    medline_task = retrieve_medlineplus_citations(query, top_k=2)
    pubmed_task = retrieve_pubmed_citations(query, top_k=2)
    openfda_task = retrieve_openfda_citations(query, top_k=1)
    trials_task = retrieve_clinicaltrials_citations(query, top_k=1)

    medline, pubmed, openfda, trials = await asyncio.gather(
        medline_task,
        pubmed_task,
        openfda_task,
        trials_task,
    )

    merged = [*(medline or []), *(pubmed or []), *(openfda or []), *(trials or [])]
    ranked = _rank_reputable_citations(merged)
    return _normalize_rank(ranked[: max(1, top_k)])
