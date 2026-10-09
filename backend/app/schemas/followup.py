from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FollowUpStatus = Literal["scheduled", "completed", "missed", "cancelled"]
FollowUpChannel = Literal["sms", "call", "whatsapp", "in_app"]


class FollowUpCreate(BaseModel):
    patient_id: int | None = None
    diagnosis_id: int | None = None
    due_at: datetime
    channel: FollowUpChannel = "sms"
    reminder_enabled: bool = True
    notes: str | None = Field(default=None, max_length=1000)


class FollowUpUpdate(BaseModel):
    due_at: datetime | None = None
    channel: FollowUpChannel | None = None
    reminder_enabled: bool | None = None
    reminder_sent: bool | None = None
    notes: str | None = Field(default=None, max_length=1000)
    outcome: str | None = Field(default=None, max_length=1000)


class FollowUpStatusUpdate(BaseModel):
    status: FollowUpStatus
    outcome: str | None = Field(default=None, max_length=1000)


class FollowUpInDB(BaseModel):
    id: int
    user_id: int
    patient_id: int | None
    diagnosis_id: int | None
    due_at: datetime
    channel: FollowUpChannel
    reminder_enabled: bool
    reminder_sent: bool
    status: FollowUpStatus
    notes: str | None
    outcome: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
