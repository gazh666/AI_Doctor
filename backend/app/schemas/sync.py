from __future__ import annotations
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


SyncOperation = Literal["create", "update", "delete"]
SyncStatus = Literal["applied", "conflict", "resolved"]
ResolutionStrategy = Literal["client_wins", "server_wins", "merge"]


class SyncRecord(BaseModel):
    entity_type: str = Field(..., min_length=2)
    entity_id: str = Field(..., min_length=1)
    operation: SyncOperation
    payload: dict[str, Any] | None = None
    client_updated_at: datetime


class SyncPushRequest(BaseModel):
    device_id: str = Field(..., min_length=2)
    records: list[SyncRecord] = Field(..., min_length=1)


class SyncPushItemResult(BaseModel):
    sync_event_id: int
    entity_type: str
    entity_id: str
    status: SyncStatus
    conflict_reason: str | None = None


class SyncPushResponse(BaseModel):
    accepted: int
    conflicts: int
    results: list[SyncPushItemResult]


class SyncEventOut(BaseModel):
    id: int
    device_id: str
    entity_type: str
    entity_id: str
    operation: SyncOperation
    payload: dict[str, Any] | None
    client_updated_at: datetime
    server_updated_at: datetime
    sync_status: SyncStatus
    conflict_reason: str | None


class SyncPullResponse(BaseModel):
    since: datetime | None
    events: list[SyncEventOut]


class SyncResolveRequest(BaseModel):
    conflict_event_id: int
    strategy: ResolutionStrategy
    merged_payload: dict[str, Any] | None = None


class SyncResolveResponse(BaseModel):
    conflict_event_id: int
    resolved_event_id: int
    strategy: ResolutionStrategy
    status: str
