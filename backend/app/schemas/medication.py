from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["low", "moderate", "high", "critical"]


class MedicationSafetyRequest(BaseModel):
    medications: list[str] = Field(..., min_length=1)
    allergies: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    age: int | None = Field(default=None, ge=0, le=120)
    pregnant: bool = False
    patient_id: int | None = None


class MedicationAlert(BaseModel):
    type: str
    detail: str
    severity: RiskLevel


class MedicationSafetyResponse(BaseModel):
    risk_level: RiskLevel
    interactions: list[MedicationAlert]
    contraindications: list[MedicationAlert]
    recommendation: str


class MedicationRecommendationRequest(BaseModel):
    condition: str = Field(..., min_length=2)
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    age: int | None = Field(default=None, ge=0, le=120)
    pregnant: bool = False


class MedicationRecommendationResponse(BaseModel):
    suggested_options: list[str]
    caution_notes: list[str]
    disclaimer: str


class MedicationSafetyInDB(BaseModel):
    id: int
    user_id: int
    patient_id: int | None
    medications_json: list[str]
    allergies_json: list[str] | None
    conditions_json: list[str] | None
    risk_level: RiskLevel
    interactions_json: list[dict] | None
    contraindications_json: list[dict] | None
    recommendation: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
