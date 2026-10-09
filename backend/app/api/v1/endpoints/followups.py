from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.models import FollowUpPlan, User
from app.db.session import get_db
from app.schemas.followup import (
    FollowUpCreate,
    FollowUpInDB,
    FollowUpStatusUpdate,
    FollowUpUpdate,
)

router = APIRouter()

DBDep = Annotated[AsyncSession, Depends(get_db)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]


@router.post("/schedule", response_model=FollowUpInDB, status_code=status.HTTP_201_CREATED)
async def schedule_followup(request: FollowUpCreate, current_user: ActiveUser, db: DBDep):
    followup = FollowUpPlan(
        user_id=current_user.id,
        patient_id=request.patient_id,
        diagnosis_id=request.diagnosis_id,
        due_at=request.due_at,
        channel=request.channel,
        reminder_enabled=request.reminder_enabled,
        notes=request.notes,
        status="scheduled",
    )
    db.add(followup)
    await db.commit()
    await db.refresh(followup)
    return followup


@router.get("/patient/{patient_id}", response_model=list[FollowUpInDB])
async def list_patient_followups(patient_id: int, current_user: ActiveUser, db: DBDep):
    result = await db.execute(
        select(FollowUpPlan)
        .where(FollowUpPlan.user_id == current_user.id, FollowUpPlan.patient_id == patient_id)
        .order_by(FollowUpPlan.due_at.desc())
    )
    return list(result.scalars().all())


@router.get("/pending", response_model=list[FollowUpInDB])
async def list_pending_followups(current_user: ActiveUser, db: DBDep):
    result = await db.execute(
        select(FollowUpPlan)
        .where(FollowUpPlan.user_id == current_user.id, FollowUpPlan.status == "scheduled")
        .order_by(FollowUpPlan.due_at.asc())
    )
    return list(result.scalars().all())


@router.patch("/{followup_id}", response_model=FollowUpInDB)
async def update_followup(
    followup_id: int,
    request: FollowUpUpdate,
    current_user: ActiveUser,
    db: DBDep,
):
    result = await db.execute(
        select(FollowUpPlan).where(FollowUpPlan.id == followup_id, FollowUpPlan.user_id == current_user.id)
    )
    followup = result.scalar_one_or_none()

    if not followup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")

    data = request.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(followup, key, value)

    followup.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(followup)
    return followup


@router.patch("/{followup_id}/status", response_model=FollowUpInDB)
async def update_followup_status(
    followup_id: int,
    request: FollowUpStatusUpdate,
    current_user: ActiveUser,
    db: DBDep,
):
    result = await db.execute(
        select(FollowUpPlan).where(FollowUpPlan.id == followup_id, FollowUpPlan.user_id == current_user.id)
    )
    followup = result.scalar_one_or_none()

    if not followup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")

    followup.status = request.status
    if request.outcome:
        followup.outcome = request.outcome
    followup.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(followup)
    return followup
