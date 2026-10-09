from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.core.config import settings
from app.core.audit_confidence import derive_confidence_band
from app.db.models import AIDecisionAudit, TriageAssessment, User
from app.db.session import get_db
from app.schemas.triage import (
    TriageAssessmentInDB,
    TriageAssessmentRequest,
    TriageAssessmentResponse,
    TriageEscalationRequest,
    TriageEscalationResponse,
    TriageProtocol,
)

router = APIRouter()

DBDep = Annotated[AsyncSession, Depends(get_db)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]


def _compute_triage(request: TriageAssessmentRequest) -> tuple[str, list[str], str, str]:
    text = request.symptoms.lower()
    red_flags: list[str] = []

    emergency_keywords = {
        "chest pain": "Possible cardiac emergency",
        "shortness of breath": "Respiratory distress risk",
        "faint": "Loss of consciousness risk",
        "unconscious": "Immediate emergency risk",
        "seizure": "Neurological emergency risk",
        "stroke": "Possible stroke signs",
        "severe bleeding": "Potential hemorrhage",
        "suicidal": "Mental health crisis",
    }

    urgent_keywords = {
        "high fever": "Possible acute infection",
        "vomiting": "Risk of dehydration",
        "dehydration": "Fluid imbalance risk",
        "pregnant": "Requires accelerated clinical review",
        "infection": "Possible worsening infection",
        "severe pain": "Needs same-day evaluation",
    }

    for keyword, reason in emergency_keywords.items():
        if keyword in text:
            red_flags.append(reason)

    vitals = request.vitals
    if vitals:
        if vitals.spo2 is not None and vitals.spo2 < 92:
            red_flags.append("Low oxygen saturation")
        if vitals.systolic_bp is not None and vitals.diastolic_bp is not None:
            if vitals.systolic_bp >= 180 or vitals.diastolic_bp >= 120:
                red_flags.append("Hypertensive crisis range blood pressure")

    if red_flags:
        return (
            "emergency",
            red_flags,
            "Critical warning signs identified during triage.",
            "Seek emergency care immediately or call local emergency services.",
        )

    urgent_signals = []
    for keyword, reason in urgent_keywords.items():
        if keyword in text:
            urgent_signals.append(reason)

    if vitals:
        if vitals.temperature_c is not None and vitals.temperature_c >= 38.5:
            urgent_signals.append("High fever threshold reached")
        if vitals.heart_rate is not None and vitals.heart_rate >= 120:
            urgent_signals.append("Tachycardia threshold reached")

    if urgent_signals:
        return (
            "urgent",
            urgent_signals,
            "Symptoms suggest a time-sensitive condition that requires rapid clinician review.",
            "Book an urgent consultation within 6-12 hours.",
        )

    return (
        "routine",
        [],
        "No immediate danger markers found in current triage data.",
        "Schedule a routine clinic visit and monitor symptoms.",
    )


@router.post("/assess", response_model=TriageAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def assess_triage(
    request: TriageAssessmentRequest,
    current_user: ActiveUser,
    db: DBDep,
):
    urgency_level, red_flags, rationale, action = _compute_triage(request)

    triage_record = TriageAssessment(
        user_id=current_user.id,
        patient_id=request.patient_id,
        symptoms_text=request.symptoms,
        age=request.age,
        vitals_json=request.vitals.model_dump() if request.vitals else None,
        risk_factors_json=request.risk_factors,
        urgency_level=urgency_level,
        red_flags_json=red_flags,
        rationale=rationale,
        recommended_action=action,
    )

    db.add(triage_record)
    confidence_band = derive_confidence_band(
        urgency_level=urgency_level,
        red_flags_count=len(red_flags),
        output_summary=action,
    )
    audit_record = AIDecisionAudit(
        user_id=current_user.id,
        source_endpoint="/api/v1/triage/assess",
        decision_type="triage",
        input_summary=request.symptoms,
        output_summary=action,
        confidence_band=confidence_band,
        urgency_level=urgency_level,
        red_flags_json=red_flags,
        model_name=settings.GEMINI_MODEL,
        model_version="v1",
        prompt_version="triage-rules-v1",
    )
    db.add(audit_record)
    await db.commit()
    await db.refresh(triage_record)

    return TriageAssessmentResponse(
        assessment_id=triage_record.id,
        urgency_level=urgency_level,
        red_flags=red_flags,
        rationale=rationale,
        recommended_action=action,
        created_at=triage_record.created_at,
    )


@router.get("/protocols", response_model=list[TriageProtocol])
async def list_triage_protocols():
    return [
        TriageProtocol(
            code="RED-001",
            urgency_level="emergency",
            description="Severe chest pain, breathing distress, neurological collapse, or critical vitals.",
            target_response_time="Immediately",
        ),
        TriageProtocol(
            code="AMBER-001",
            urgency_level="urgent",
            description="Time-sensitive symptoms with moderate physiological instability.",
            target_response_time="Within 6-12 hours",
        ),
        TriageProtocol(
            code="GREEN-001",
            urgency_level="routine",
            description="Stable symptoms without red flags or urgent physiological signals.",
            target_response_time="Within 24-72 hours",
        ),
    ]


@router.post("/escalate", response_model=TriageEscalationResponse)
async def escalate_triage(
    request: TriageEscalationRequest,
    current_user: ActiveUser,
    db: DBDep,
):
    result = await db.execute(
        select(TriageAssessment).where(
            TriageAssessment.id == request.assessment_id,
            TriageAssessment.user_id == current_user.id,
        )
    )
    triage_record = result.scalar_one_or_none()

    if not triage_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage assessment not found",
        )

    triage_record.escalated = True
    triage_record.escalation_reason = request.reason

    await db.commit()

    ticket = f"TRIAGE-{triage_record.id}-{int(datetime.now(timezone.utc).timestamp())}"
    return TriageEscalationResponse(
        assessment_id=triage_record.id,
        escalation_ticket=ticket,
        status="escalated",
        message="Case escalated successfully for clinician review.",
    )


@router.get("/history", response_model=list[TriageAssessmentInDB])
async def get_triage_history(current_user: ActiveUser, db: DBDep):
    result = await db.execute(
        select(TriageAssessment)
        .where(TriageAssessment.user_id == current_user.id)
        .order_by(TriageAssessment.created_at.desc())
    )
    return list(result.scalars().all())
