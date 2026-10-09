from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from typing import Any, List, Optional


class RagUploadResponse(BaseModel):
    knowledge_base_id: str
    filename: str
    size_bytes: int
    chunks_indexed: int
    truncated: bool = False
    message: str


class RagQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Question about uploaded medical report content")
    top_k: int = Field(4, ge=1, le=10)


class RagCitation(BaseModel):
    id: int
    rank: int
    title: str
    source: Optional[str] = None
    excerpt: str
    provider: Optional[str] = None
    similarity: float = 0.0
    evidence_level: Optional[str] = None
    published_at: Optional[str] = None
    last_verified_at: Optional[str] = None


class RagQueryResponse(BaseModel):
    answer: str
    matched_chunks: int
    citations: List[RagCitation] = Field(default_factory=list)


class TrustedSourceCreateRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=60)
    title: str = Field(..., min_length=8, max_length=300)
    url: HttpUrl
    excerpt: str = Field(..., min_length=20)
    condition_tags: List[str] = Field(default_factory=list)
    evidence_level: Optional[str] = Field(default="guideline")
    published_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None


class TrustedSourceResponse(BaseModel):
    id: int
    provider: str
    title: str
    url: str
    excerpt: str
    condition_tags: List[str] = Field(default_factory=list)
    evidence_level: Optional[str] = None
    published_at: Optional[str] = None
    last_verified_at: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None


class TrustedSourceSeedResponse(BaseModel):
    inserted: int
    skipped_existing: int
