from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


UrgencyLevel = Literal["emergency", "urgent", "routine"]


class TriageVitals(BaseModel):
    temperature_c: float | None = None
    heart_rate: int | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    spo2: int | None = None


class TriageAssessmentRequest(BaseModel):
    symptoms: str = Field(..., min_length=3)
    age: int | None = Field(default=None, ge=0, le=120)
    patient_id: int | None = None
    risk_factors: list[str] = Field(default_factory=list)
    vitals: TriageVitals | None = None


class TriageAssessmentResponse(BaseModel):
    assessment_id: int
    urgency_level: UrgencyLevel
    red_flags: list[str]
    rationale: str
    recommended_action: str
    created_at: datetime


class TriageProtocol(BaseModel):
    code: str
    urgency_level: UrgencyLevel
    description: str
    target_response_time: str


class TriageEscalationRequest(BaseModel):
    assessment_id: int
    reason: str = Field(..., min_length=5)


class TriageEscalationResponse(BaseModel):
    assessment_id: int
    escalation_ticket: str
    status: str
    message: str


class TriageAssessmentInDB(BaseModel):
    id: int
    user_id: int | None
    patient_id: int | None
    symptoms_text: str
    age: int | None
    urgency_level: UrgencyLevel
    red_flags_json: list[str] | None
    rationale: str | None
    recommended_action: str
    escalated: bool
    escalation_reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
