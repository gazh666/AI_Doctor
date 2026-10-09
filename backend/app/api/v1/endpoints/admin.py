"""
Admin endpoints for system-wide analytics and management.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import (
    AIDecisionAudit,
    ChatHistory,
    Diagnosis,
    ImageAnalysis,
    Patient,
    User,
    VoiceInteraction,
)
from app.core.deps import get_current_admin_user
from app.core.config import settings
from app.schemas.admin import (
    AdminAuditFeedbackResponse,
    AdminAuditFeedbackUpdateRequest,
    AdminAuditLogsResponse,
    AdminAuditSessionResponse,
    AdminBiasCheckResponse,
    AdminSeedDemoAuditResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin Analytics"])

# Modern Dependency Aliases (2026 Best Practice)
DBDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[User, Depends(get_current_admin_user)]

@router.get("/stats/overview")
async def get_admin_stats_overview(
    current_admin: AdminDep,
    db: DBDep
):
    """
    Retrieves global system metrics using optimized SQLAlchemy 2.0 scalar execution.
    """
    # Use timezone-aware UTC for 2026 standards
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Global User Stats
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.last_login >= thirty_days_ago)
    )

    # Diagnosis Analytics
    total_diagnoses = await db.scalar(select(func.count(Diagnosis.id)))
    diagnoses_today = await db.scalar(
        select(func.count(Diagnosis.id)).where(Diagnosis.created_at >= today_start)
    )

    # Feature Adoption Metrics
    total_chats = await db.scalar(
        select(func.count(func.distinct(ChatHistory.session_id)))
    )
    total_voice = await db.scalar(select(func.count(VoiceInteraction.id)))
    total_images = await db.scalar(select(func.count(ImageAnalysis.id)))

    return {
        "users": {
            "total": total_users or 0,
            "active_30_days": active_users or 0
        },
        "diagnoses": {
            "total": total_diagnoses or 0,
            "today": diagnoses_today or 0
        },
        "features": {
            "chat_sessions": total_chats or 0,
            "voice_interactions": total_voice or 0,
            "image_analyses": total_images or 0
        }
    }

@router.get("/stats/diagnoses-by-day")
async def get_diagnoses_by_day(
    db: DBDep,
    current_admin: AdminDep,
    days: int = 30
):
    """Retrieves time-series data for diagnosis trends."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = (
        select(
            func.date(Diagnosis.created_at).label('date'),
            func.count(Diagnosis.id).label('count')
        )
        .where(Diagnosis.created_at >= start_date)
        .group_by(func.date(Diagnosis.created_at))
        .order_by(func.date(Diagnosis.created_at))
    )
    
    result = await db.execute(query)
    return [
        {"date": row.date.isoformat(), "count": row.count}
        for row in result.all()
    ]

@router.get("/stats/distribution")
async def get_global_distributions(current_admin: AdminDep, db: DBDep):
    """
    Aggregates global severity and urgency distributions.
    Demonstrates efficient grouping for data visualization.
    """
    # Severity Distribution
    sev_result = await db.execute(
        select(Diagnosis.severity, func.count(Diagnosis.id)).group_by(Diagnosis.severity)
    )
    
    # Urgency Distribution
    urg_result = await db.execute(
        select(Diagnosis.urgency_level, func.count(Diagnosis.id)).group_by(Diagnosis.urgency_level)
    )
    
    return {
        "severity": {sev: count for sev, count in sev_result.all()},
        "urgency": {urg: count for urg, count in urg_result.all()}
    }

@router.get("/users/recent")
async def get_recent_users(
    db: DBDep,
    current_admin: AdminDep,
    limit: int = 10
):
    """Retrieves the latest user registrations."""
    query = select(User).order_by(desc(User.created_at)).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "created_at": u.created_at,
            "last_login": u.last_login
        }
        for u in users
    ]

@router.get("/diagnoses/recent")
async def get_recent_diagnoses(
    db: DBDep,
    current_admin: AdminDep,
    limit: int = 10
):
    """Global feed of recent clinical activities."""
    query = select(Diagnosis).order_by(desc(Diagnosis.created_at)).limit(limit)
    result = await db.execute(query)
    diagnoses = result.scalars().all()
    
    return [
        {
            "id": d.id,
            "user_id": d.user_id,
            "diagnosis": d.diagnosis,
            "severity": d.severity,
            "urgency_level": d.urgency_level,
            "confidence": d.confidence,
            "created_at": d.created_at
        }
        for d in diagnoses
    ]


@router.get("/audit/logs", response_model=AdminAuditLogsResponse)
async def get_audit_logs(
    current_admin: AdminDep,
    db: DBDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, description="Search query over input/output/model/session"),
    confidence_band: str | None = Query(default=None, description="Filter by low/medium/high"),
    decision_type: str | None = Query(default=None, description="Filter by chat/triage/symptom_analysis"),
    overridden: bool | None = Query(default=None, description="Filter override_applied true/false"),
):
    """Paginated deep-dive list of AI decision audits."""
    base_query = select(AIDecisionAudit)

    if q:
        search = f"%{q.strip()}%"
        base_query = base_query.where(
            or_(
                AIDecisionAudit.input_summary.ilike(search),
                AIDecisionAudit.output_summary.ilike(search),
                AIDecisionAudit.model_name.ilike(search),
                AIDecisionAudit.decision_type.ilike(search),
                AIDecisionAudit.session_id.ilike(search),
            )
        )
    if confidence_band:
        base_query = base_query.where(AIDecisionAudit.confidence_band.ilike(confidence_band.strip()))
    if decision_type:
        base_query = base_query.where(AIDecisionAudit.decision_type.ilike(decision_type.strip()))
    if overridden is not None:
        base_query = base_query.where(AIDecisionAudit.override_applied == overridden)

    count_query = select(func.count()).select_from(base_query.subquery())
    total = int((await db.scalar(count_query)) or 0)

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(desc(AIDecisionAudit.created_at)).offset(offset).limit(page_size)
    )
    rows = result.scalars().all()

    return {
        "items": [
            {
                "id": row.id,
                "session_id": row.session_id,
                "source_endpoint": row.source_endpoint,
                "decision_type": row.decision_type,
                "input_summary": row.input_summary,
                "output_summary": row.output_summary,
                "confidence_band": row.confidence_band,
                "urgency_level": row.urgency_level,
                "model_name": row.model_name,
                "model_version": row.model_version,
                "prompt_version": row.prompt_version,
                "override_applied": row.override_applied,
                "clinician_feedback": row.clinician_feedback,
                "created_at": row.created_at,
            }
            for row in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.post("/audit/seed-demo", response_model=AdminSeedDemoAuditResponse)
async def seed_demo_audit_logs(
    current_admin: AdminDep,
    db: DBDep,
    count: int = Query(default=20, ge=1, le=200),
):
    """Seed synthetic audit rows for demo/testing. Disabled in production."""
    env = (settings.ENVIRONMENT or "production").lower()
    if env in {"production", "prod"}:
        raise HTTPException(status_code=403, detail="Demo seeding is disabled in production")

    templates = [
        ("chat", "low", "Uncertain output. Needs clinician confirmation.", "URGENT"),
        ("chat", "medium", "Routine advisory generated.", "ROUTINE"),
        ("symptom_analysis", "high", "High confidence recommendation generated.", "ROUTINE"),
        ("triage", "high", "Emergency escalation recommended with strong evidence.", "EMERGENCY"),
    ]

    now = datetime.now(timezone.utc)
    for i in range(count):
        decision_type, band, output_text, urgency = templates[i % len(templates)]
        db.add(
            AIDecisionAudit(
                user_id=current_admin.id,
                session_id=str(uuid.uuid4()),
                source_endpoint="/api/v1/admin/audit/seed-demo",
                decision_type=decision_type,
                input_summary=f"Synthetic demo input #{i + 1}",
                output_summary=output_text,
                confidence_band=band,
                urgency_level=urgency,
                red_flags_json=["demo-flag"] if urgency == "EMERGENCY" else [],
                model_name=settings.GEMINI_MODEL,
                model_version="demo-v1",
                prompt_version="demo-seed-v1",
                override_applied=(i % 7 == 0),
                clinician_feedback="Demo seeded row for UI testing." if i % 9 == 0 else None,
                created_at=now - timedelta(minutes=i),
            )
        )

    await db.commit()
    return {"inserted": count, "environment": settings.ENVIRONMENT}


@router.get("/audit/sessions/{session_id}", response_model=AdminAuditSessionResponse)
async def get_audit_session_history(
    session_id: str,
    current_admin: AdminDep,
    db: DBDep,
):
    """Fetch full chat transcript for an audited session."""
    audit_exists = await db.scalar(
        select(func.count(AIDecisionAudit.id)).where(AIDecisionAudit.session_id == session_id)
    )
    if not audit_exists:
        raise HTTPException(status_code=404, detail="No audit log found for this session")

    result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at.asc())
    )
    messages = result.scalars().all()

    return {
        "session_id": session_id,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at,
            }
            for msg in messages
        ],
    }


@router.patch("/audit/{audit_id}/feedback", response_model=AdminAuditFeedbackResponse)
async def update_audit_feedback(
    audit_id: int,
    payload: AdminAuditFeedbackUpdateRequest,
    current_admin: AdminDep,
    db: DBDep,
):
    """Save clinician feedback and override toggle for an AI decision record."""
    result = await db.execute(select(AIDecisionAudit).where(AIDecisionAudit.id == audit_id))
    audit_row = result.scalar_one_or_none()
    if audit_row is None:
        raise HTTPException(status_code=404, detail="Audit log not found")

    audit_row.clinician_feedback = payload.clinician_feedback
    audit_row.override_applied = payload.override_applied
    await db.commit()
    await db.refresh(audit_row)

    return {
        "id": audit_row.id,
        "override_applied": audit_row.override_applied,
        "clinician_feedback": audit_row.clinician_feedback,
        "updated": True,
    }


@router.get("/analytics/bias-check", response_model=AdminBiasCheckResponse)
async def get_bias_check_analytics(
    current_admin: AdminDep,
    db: DBDep,
):
    """Demographic distributions for urgency and confidence (gender/age groups)."""
    result = await db.execute(
        select(
            Diagnosis.urgency_level,
            Diagnosis.confidence,
            Patient.gender,
            Patient.age,
        )
        .select_from(Diagnosis)
        .outerjoin(Patient, Diagnosis.patient_id == Patient.id)
    )
    rows = result.all()

    def _age_group(age: int | None) -> str:
        if age is None:
            return "Unknown"
        if age < 18:
            return "0-17"
        if age < 36:
            return "18-35"
        if age < 61:
            return "36-60"
        return "60+"

    def _confidence_band(value: float | None) -> str:
        if value is None:
            return "Unknown"
        if value < 0.40:
            return "Low"
        if value < 0.75:
            return "Medium"
        return "High"

    gender_urgency_counts: dict[tuple[str, str], int] = {}
    gender_conf_counts: dict[tuple[str, str], int] = {}
    age_urgency_counts: dict[tuple[str, str], int] = {}
    age_conf_counts: dict[tuple[str, str], int] = {}

    for row in rows:
        demographic_gender = row.gender or "Unknown"
        demographic_age = _age_group(row.age)
        urgency = (row.urgency_level or "UNKNOWN").upper()
        conf_band = _confidence_band(row.confidence)

        gender_urgency_counts[(demographic_gender, urgency)] = (
            gender_urgency_counts.get((demographic_gender, urgency), 0) + 1
        )
        gender_conf_counts[(demographic_gender, conf_band)] = (
            gender_conf_counts.get((demographic_gender, conf_band), 0) + 1
        )
        age_urgency_counts[(demographic_age, urgency)] = (
            age_urgency_counts.get((demographic_age, urgency), 0) + 1
        )
        age_conf_counts[(demographic_age, conf_band)] = (
            age_conf_counts.get((demographic_age, conf_band), 0) + 1
        )

    return {
        "gender_urgency": [
            {"demographic": demo, "urgency_level": urgency, "count": count}
            for (demo, urgency), count in sorted(gender_urgency_counts.items())
        ],
        "gender_confidence": [
            {"demographic": demo, "confidence_band": band, "count": count}
            for (demo, band), count in sorted(gender_conf_counts.items())
        ],
        "age_urgency": [
            {"demographic": demo, "urgency_level": urgency, "count": count}
            for (demo, urgency), count in sorted(age_urgency_counts.items())
        ],
        "age_confidence": [
            {"demographic": demo, "confidence_band": band, "count": count}
            for (demo, band), count in sorted(age_conf_counts.items())
        ],
    }
