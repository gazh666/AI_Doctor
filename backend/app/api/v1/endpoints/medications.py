from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.models import MedicationSafetyCheck, User
from app.db.session import get_db
from app.schemas.medication import (
    MedicationAlert,
    MedicationRecommendationRequest,
    MedicationRecommendationResponse,
    MedicationSafetyRequest,
    MedicationSafetyResponse,
)

router = APIRouter()

DBDep = Annotated[AsyncSession, Depends(get_db)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]


INTERACTION_RULES = {
    frozenset(["warfarin", "aspirin"]): (
        "Increased bleeding risk when combined.",
        "high",
    ),
    frozenset(["ibuprofen", "lisinopril"]): (
        "NSAIDs may reduce antihypertensive effect and stress kidneys.",
        "moderate",
    ),
    frozenset(["metformin", "alcohol"]): (
        "Elevated risk of lactic acidosis with high alcohol intake.",
        "high",
    ),
}

CONTRAINDICATION_RULES = {
    "pregnant": {
        "isotretinoin": ("Teratogenic risk during pregnancy.", "critical"),
        "warfarin": ("Potential fetal bleeding and malformations.", "critical"),
    },
    "asthma": {
        "aspirin": ("Can trigger bronchospasm in aspirin-sensitive asthma.", "high"),
    },
    "renal_disease": {
        "ibuprofen": ("May worsen renal function.", "high"),
    },
}

CONDITION_TREATMENT_OPTIONS = {
    "fever": ["paracetamol"],
    "pain": ["paracetamol", "ibuprofen"],
    "hypertension": ["lisinopril", "amlodipine"],
    "diabetes": ["metformin"],
    "allergic rhinitis": ["cetirizine", "loratadine"],
}


def _max_risk(current: str, candidate: str) -> str:
    order = {"low": 0, "moderate": 1, "high": 2, "critical": 3}
    return candidate if order[candidate] > order[current] else current


def _normalize(values: list[str]) -> list[str]:
    return [v.strip().lower() for v in values if v.strip()]


@router.post("/check-interactions", response_model=MedicationSafetyResponse, status_code=status.HTTP_200_OK)
async def check_interactions(
    request: MedicationSafetyRequest,
    current_user: ActiveUser,
    db: DBDep,
):
    meds = _normalize(request.medications)
    allergies = _normalize(request.allergies)
    conditions = _normalize(request.conditions)

    interactions: list[MedicationAlert] = []
    contraindications: list[MedicationAlert] = []
    risk_level = "low"

    # Pairwise interaction detection
    for i in range(len(meds)):
        for j in range(i + 1, len(meds)):
            pair = frozenset([meds[i], meds[j]])
            if pair in INTERACTION_RULES:
                detail, severity = INTERACTION_RULES[pair]
                interactions.append(
                    MedicationAlert(
                        type="interaction",
                        detail=f"{meds[i]} + {meds[j]}: {detail}",
                        severity=severity,
                    )
                )
                risk_level = _max_risk(risk_level, severity)

    # Allergy-based contraindication
    for med in meds:
        if med in allergies:
            contraindications.append(
                MedicationAlert(
                    type="allergy",
                    detail=f"Allergy conflict detected for medication: {med}.",
                    severity="critical",
                )
            )
            risk_level = _max_risk(risk_level, "critical")

    # Pregnancy checks
    if request.pregnant:
        for med in meds:
            rule = CONTRAINDICATION_RULES["pregnant"].get(med)
            if rule:
                detail, severity = rule
                contraindications.append(
                    MedicationAlert(
                        type="pregnancy",
                        detail=f"{med}: {detail}",
                        severity=severity,
                    )
                )
                risk_level = _max_risk(risk_level, severity)

    # Condition checks
    for condition in conditions:
        if condition not in CONTRAINDICATION_RULES:
            continue
        condition_rules = CONTRAINDICATION_RULES[condition]
        for med in meds:
            rule = condition_rules.get(med)
            if not rule:
                continue
            detail, severity = rule
            contraindications.append(
                MedicationAlert(
                    type="condition",
                    detail=f"{condition} with {med}: {detail}",
                    severity=severity,
                )
            )
            risk_level = _max_risk(risk_level, severity)

    recommendation = "Medication profile appears acceptable for routine review."
    if risk_level in {"high", "critical"}:
        recommendation = "Consult a clinician before taking this medication combination."
    elif risk_level == "moderate":
        recommendation = "Use caution and monitor symptoms; consider clinician review."

    safety_log = MedicationSafetyCheck(
        user_id=current_user.id,
        patient_id=request.patient_id,
        medications_json=meds,
        allergies_json=allergies,
        conditions_json=conditions,
        risk_level=risk_level,
        interactions_json=[item.model_dump() for item in interactions],
        contraindications_json=[item.model_dump() for item in contraindications],
        recommendation=recommendation,
    )
    db.add(safety_log)
    await db.commit()

    return MedicationSafetyResponse(
        risk_level=risk_level,
        interactions=interactions,
        contraindications=contraindications,
        recommendation=recommendation,
    )


@router.post("/recommend", response_model=MedicationRecommendationResponse)
async def recommend_medication(
    request: MedicationRecommendationRequest,
):
    condition = request.condition.strip().lower()
    current = set(_normalize(request.current_medications))
    allergies = set(_normalize(request.allergies))

    options = CONDITION_TREATMENT_OPTIONS.get(condition, ["paracetamol"])
    safe_options = [option for option in options if option not in allergies and option not in current]

    cautions = []
    if request.pregnant:
        cautions.append("Verify pregnancy-safe medication with a clinician before use.")
    if request.age is not None and request.age < 12:
        cautions.append("Pediatric dosing and formulation review required.")

    if not safe_options:
        safe_options = ["No safe auto-suggestion available from rules"]
        cautions.append("Medication recommendation needs direct clinician decision.")

    return MedicationRecommendationResponse(
        suggested_options=safe_options,
        caution_notes=cautions,
        disclaimer="This is decision support and not a prescription.",
    )
