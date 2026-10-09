from __future__ import annotations
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.models import SyncEvent, User
from app.db.session import get_db
from app.schemas.sync import (
    SyncEventOut,
    SyncPullResponse,
    SyncPushItemResult,
    SyncPushRequest,
    SyncPushResponse,
    SyncResolveRequest,
    SyncResolveResponse,
)

router = APIRouter()

DBDep = Annotated[AsyncSession, Depends(get_db)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]


@router.post("/push", response_model=SyncPushResponse, status_code=status.HTTP_200_OK)
async def push_sync(request: SyncPushRequest, current_user: ActiveUser, db: DBDep):
    results: list[SyncPushItemResult] = []
    accepted = 0
    conflicts = 0

    for record in request.records:
        latest_query = (
            select(SyncEvent)
            .where(
                and_(
                    SyncEvent.user_id == current_user.id,
                    SyncEvent.entity_type == record.entity_type,
                    SyncEvent.entity_id == record.entity_id,
                )
            )
            .order_by(SyncEvent.server_updated_at.desc())
        )
        latest_result = await db.execute(latest_query)
        latest_event = latest_result.scalars().first()

        is_conflict = False
        reason = None
        if latest_event and latest_event.server_updated_at > record.client_updated_at:
            is_conflict = True
            reason = "Server has newer version than client update timestamp"

        sync_event = SyncEvent(
            user_id=current_user.id,
            device_id=request.device_id,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            operation=record.operation,
            payload_json=record.payload,
            client_updated_at=record.client_updated_at,
            server_updated_at=datetime.now(timezone.utc),
            sync_status="conflict" if is_conflict else "applied",
            conflict_reason=reason,
        )

        db.add(sync_event)
        await db.flush()

        if is_conflict:
            conflicts += 1
        else:
            accepted += 1

        results.append(
            SyncPushItemResult(
                sync_event_id=sync_event.id,
                entity_type=record.entity_type,
                entity_id=record.entity_id,
                status=sync_event.sync_status,
                conflict_reason=reason,
            )
        )

    await db.commit()
    return SyncPushResponse(accepted=accepted, conflicts=conflicts, results=results)


@router.get("/pull", response_model=SyncPullResponse)
async def pull_sync(
    current_user: ActiveUser,
    db: DBDep,
    since: datetime | None = Query(default=None),
):
    stmt = select(SyncEvent).where(SyncEvent.user_id == current_user.id)
    if since:
        stmt = stmt.where(SyncEvent.server_updated_at > since)

    stmt = stmt.order_by(SyncEvent.server_updated_at.asc())
    result = await db.execute(stmt)
    events = list(result.scalars().all())

    return SyncPullResponse(
        since=since,
        events=[
            SyncEventOut(
                id=item.id,
                device_id=item.device_id,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                operation=item.operation,
                payload=item.payload_json,
                client_updated_at=item.client_updated_at,
                server_updated_at=item.server_updated_at,
                sync_status=item.sync_status,
                conflict_reason=item.conflict_reason,
            )
            for item in events
        ],
    )


@router.post("/conflicts/resolve", response_model=SyncResolveResponse)
async def resolve_sync_conflict(request: SyncResolveRequest, current_user: ActiveUser, db: DBDep):
    conflict_result = await db.execute(
        select(SyncEvent).where(
            SyncEvent.id == request.conflict_event_id,
            SyncEvent.user_id == current_user.id,
            SyncEvent.sync_status == "conflict",
        )
    )
    conflict_event = conflict_result.scalar_one_or_none()

    if not conflict_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict event not found")

    resolution_payload = conflict_event.payload_json
    if request.strategy == "merge":
        if not request.merged_payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="merged_payload is required for merge strategy",
            )
        resolution_payload = request.merged_payload

    if request.strategy == "server_wins":
        resolution_payload = None

    conflict_event.sync_status = "resolved"
    conflict_event.resolution_strategy = request.strategy
    conflict_event.resolved_by_user = True

    resolved_event = SyncEvent(
        user_id=current_user.id,
        device_id=conflict_event.device_id,
        entity_type=conflict_event.entity_type,
        entity_id=conflict_event.entity_id,
        operation="update",
        payload_json=resolution_payload,
        client_updated_at=datetime.now(timezone.utc),
        server_updated_at=datetime.now(timezone.utc),
        sync_status="applied",
        conflict_reason=None,
        resolution_strategy=request.strategy,
        resolved_by_user=True,
    )

    db.add(resolved_event)
    await db.commit()
    await db.refresh(resolved_event)

    return SyncResolveResponse(
        conflict_event_id=conflict_event.id,
        resolved_event_id=resolved_event.id,
        strategy=request.strategy,
        status="resolved",
    )
