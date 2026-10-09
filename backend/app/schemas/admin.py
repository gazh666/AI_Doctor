from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel, Field


class AdminAuditLogItem(BaseModel):
    id: int
    session_id: str | None
    source_endpoint: str
    decision_type: str
    input_summary: str | None
    output_summary: str | None
    confidence_band: str | None
    urgency_level: str | None
    model_name: str
    model_version: str | None
    prompt_version: str | None
    override_applied: bool
    clinician_feedback: str | None
    created_at: datetime


class AdminAuditLogsResponse(BaseModel):
    items: list[AdminAuditLogItem]
    page: int
    page_size: int
    total: int


class AdminAuditSessionMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class AdminAuditSessionResponse(BaseModel):
    session_id: str
    messages: list[AdminAuditSessionMessage]


class AdminAuditFeedbackUpdateRequest(BaseModel):
    clinician_feedback: str | None = Field(default=None, max_length=4000)
    override_applied: bool = False


class AdminAuditFeedbackResponse(BaseModel):
    id: int
    override_applied: bool
    clinician_feedback: str | None
    updated: bool


class BiasUrgencyDistributionRow(BaseModel):
    demographic: str
    urgency_level: str
    count: int


class BiasConfidenceDistributionRow(BaseModel):
    demographic: str
    confidence_band: str
    count: int


class AdminBiasCheckResponse(BaseModel):
    gender_urgency: list[BiasUrgencyDistributionRow]
    gender_confidence: list[BiasConfidenceDistributionRow]
    age_urgency: list[BiasUrgencyDistributionRow]
    age_confidence: list[BiasConfidenceDistributionRow]


class AdminSeedDemoAuditResponse(BaseModel):
    inserted: int
    environment: str
