from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.models import AIDecisionAudit, User
from app.db.session import get_db
from app.schemas.audit import (
    AuditDecisionOut,
    AuditFeedbackRequest,
    AuditFeedbackResponse,
    ModelUsageItem,
    ModelUsageResponse,
)

router = APIRouter()

DBDep = Annotated[AsyncSession, Depends(get_db)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]


@router.get("/decision/{session_id}", response_model=list[AuditDecisionOut])
async def get_decision_audit(session_id: str, current_user: ActiveUser, db: DBDep):
    result = await db.execute(
        select(AIDecisionAudit)
        .where(
            AIDecisionAudit.session_id == session_id,
            or_(AIDecisionAudit.user_id == current_user.id, AIDecisionAudit.user_id.is_(None)),
        )
        .order_by(AIDecisionAudit.created_at.asc())
    )
    return list(result.scalars().all())


@router.get("/model-usage", response_model=ModelUsageResponse)
async def get_model_usage(current_user: ActiveUser, db: DBDep):
    stmt = (
        select(
            AIDecisionAudit.model_name,
            func.count(AIDecisionAudit.id).label("calls"),
            func.sum(case((AIDecisionAudit.override_applied.is_(True), 1), else_=0)).label("overridden"),
        )
        .where(AIDecisionAudit.user_id == current_user.id)
        .group_by(AIDecisionAudit.model_name)
        .order_by(func.count(AIDecisionAudit.id).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    usage = [
        ModelUsageItem(
            model_name=row.model_name,
            calls=int(row.calls or 0),
            overridden=int(row.overridden or 0),
        )
        for row in rows
    ]

    total_calls = sum(item.calls for item in usage)
    return ModelUsageResponse(total_calls=total_calls, usage=usage)


@router.post("/feedback", response_model=AuditFeedbackResponse, status_code=status.HTTP_200_OK)
async def submit_audit_feedback(
    request: AuditFeedbackRequest,
    current_user: ActiveUser,
    db: DBDep,
):
    result = await db.execute(
        select(AIDecisionAudit).where(
            AIDecisionAudit.id == request.audit_id,
            or_(AIDecisionAudit.user_id == current_user.id, AIDecisionAudit.user_id.is_(None)),
        )
    )
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit record not found")

    if audit.user_id is None:
        # Backfill ownership for older/system-generated audit rows
        audit.user_id = current_user.id

    audit.override_applied = request.override_applied
    audit.override_reason = request.override_reason
    audit.clinician_feedback = request.clinician_feedback

    await db.commit()

    return AuditFeedbackResponse(
        audit_id=audit.id,
        updated=True,
        message="Audit feedback saved successfully.",
    )
