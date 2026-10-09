"""
Pydantic schemas for user statistics and dashboard visualization.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Annotated

from pydantic import BaseModel, ConfigDict, Field


class DiagnosisHistory(BaseModel):
    """Schema for individual medical diagnosis records."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique identifier for the diagnosis")
    diagnosis: str = Field(..., description="The clinical name of the identified condition")
    confidence: float = Field(..., ge=0, le=1.0, description="Model confidence score (0.0 - 1.0)")
    severity: str = Field(..., pattern="^(Low|Medium|High|Critical)$")
    urgency_level: str = Field(..., description="Triage urgency (e.g., Routine, Urgent, Emergency)")
    created_at: datetime = Field(default_factory=datetime.now)


class UserDashboard(BaseModel):
    """Aggregate schema for the main user dashboard overview."""
    total_diagnoses: int = Field(0, ge=0)
    recent_diagnoses: list[DiagnosisHistory] = Field(default_factory=list)
    total_chat_sessions: int = Field(0, ge=0)
    total_voice_interactions: int = Field(0, ge=0)
    total_image_analyses: int = Field(0, ge=0)
    last_activity: Optional[datetime] = None


class UserStats(BaseModel):
    """Deep-dive statistics for data visualization components."""
    # Using dict[str, int] for stricter typing in 2026
    diagnoses_by_severity: dict[str, int] = Field(
        default_factory=lambda: {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    )
    diagnoses_by_month: dict[str, int] = Field(default_factory=dict)
    
    # Common symptoms with frequency counts
    most_common_symptoms: list[dict[str, str | int]] = Field(default_factory=list)