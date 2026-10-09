"""
Pydantic schemas for clinical appointment management.
"""

from datetime import datetime
from typing import Optional, Annotated

from pydantic import BaseModel, ConfigDict, Field


class AppointmentBase(BaseModel):
    """Core attributes for medical appointments."""
    # Use pattern validation to enforce specific clinical types in 2026
    appointment_type: str = Field(
        ..., 
        pattern="^(consultation|followup|emergency)$",
        description="Type of medical visit: consultation, followup, or emergency"
    )
    scheduled_date: datetime = Field(..., description="The planned date and time for the visit")
    duration_minutes: int = Field(30, ge=15, le=120, description="Duration in minutes (15-120)")
    notes: Optional[str] = Field(None, max_length=500, description="Additional clinical notes")


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment entry."""
    patient_id: Optional[int] = Field(None, description="Optional link to a specific patient record")


class AppointmentUpdate(BaseModel):
    """Schema for modifying existing appointment details."""
    scheduled_date: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=120)
    notes: Optional[str] = Field(None, max_length=500)
    # Status state machine enforcement
    status: Optional[str] = Field(
        None, 
        pattern="^(scheduled|completed|cancelled|no_show)$"
    )


class AppointmentInDB(AppointmentBase):
    """Full appointment representation as stored in the database."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique primary key")
    user_id: int = Field(..., description="ID of the user who owns the record")
    status: str = Field("scheduled")
    created_at: datetime = Field(default_factory=datetime.now)