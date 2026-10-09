from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ConfidenceBand = Literal["low", "medium", "high"]


class AuditDecisionOut(BaseModel):
    id: int
    session_id: str | None
    source_endpoint: str
    decision_type: str
    input_summary: str | None
    output_summary: str | None
    confidence_band: ConfidenceBand | None
    urgency_level: str | None
    red_flags_json: list[str] | None
    model_name: str
    model_version: str | None
    prompt_version: str | None
    override_applied: bool
    override_reason: str | None
    clinician_feedback: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelUsageItem(BaseModel):
    model_name: str
    calls: int
    overridden: int


class ModelUsageResponse(BaseModel):
    total_calls: int
    usage: list[ModelUsageItem]


class AuditFeedbackRequest(BaseModel):
    audit_id: int
    override_applied: bool = False
    override_reason: str | None = Field(default=None, max_length=1000)
    clinician_feedback: str | None = Field(default=None, max_length=1000)


class AuditFeedbackResponse(BaseModel):
    audit_id: int
    updated: bool
    message: str
