import logging
import math
from typing import Any

from app.services.agents.state import AgentState
from app.services.notification.notification_service import notification_service

logger = logging.getLogger(__name__)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def get_nearby_clinics(lat: float, lng: float, limit: int = 3) -> list[dict[str, Any]]:
    """Mock CHC lookup tool used by the emergency node.

    Generates location-relative facilities so emergency actions stay useful
    regardless of the user's region.
    """
    clinic_catalog = [
        {
            "name": "Primary Community Health Centre",
            "contact_number": "+91-98765-11001",
            "coordinates": {"lat": round(lat + 0.012, 6), "lng": round(lng + 0.008, 6)},
        },
        {
            "name": "Rural Block CHC - South",
            "contact_number": "+91-98765-11002",
            "coordinates": {"lat": round(lat - 0.017, 6), "lng": round(lng + 0.006, 6)},
        },
        {
            "name": "District Community Health Centre",
            "contact_number": "+91-98765-11003",
            "coordinates": {"lat": round(lat + 0.019, 6), "lng": round(lng - 0.011, 6)},
        },
        {
            "name": "Emergency Stabilization Unit - CHC",
            "contact_number": "+91-98765-11004",
            "coordinates": {"lat": round(lat - 0.009, 6), "lng": round(lng - 0.014, 6)},
        },
    ]

    ranked: list[dict[str, Any]] = []
    for clinic in clinic_catalog:
        clinic_lat = clinic["coordinates"]["lat"]
        clinic_lng = clinic["coordinates"]["lng"]
        distance_km = _haversine_km(lat, lng, clinic_lat, clinic_lng)
        ranked.append(
            {
                **clinic,
                "distance_km": round(distance_km, 2),
            }
        )

    ranked.sort(key=lambda row: row["distance_km"])
    return ranked[:limit]


def _first_aid_from_flags(red_flags: list[str]) -> list[str]:
    joined = " ".join(red_flags).lower()
    if "bleeding" in joined:
        return [
            "Apply direct pressure with a clean cloth and keep pressure continuous.",
            "Keep the patient lying down and monitor for dizziness or confusion.",
        ]
    if "breath" in joined:
        return [
            "Sit the patient upright and loosen tight clothing around neck/chest.",
            "Do not give food or drink while breathing is labored.",
        ]
    return [
        "Keep the patient calm, seated upright, and avoid physical exertion.",
        "Do not give oral medication unless already prescribed for this event.",
    ]


async def emergency_action_node(state: AgentState) -> AgentState:
    location = state.get("user_location") or {}
    lat = float(location.get("lat", 28.6139))
    lng = float(location.get("lng", 77.2090))

    detected_red_flags = (
        (state.get("symptom_analysis") or {}).get("red_flags")
        or (state.get("triage_result") or {}).get("red_flags")
        or []
    )
    nearby_facilities = get_nearby_clinics(lat=lat, lng=lng, limit=3)
    first_aid = _first_aid_from_flags(detected_red_flags)

    emergency_info = {
        "status": "CRITICAL",
        "user_location": {"lat": lat, "lng": lng},
        "red_flags": detected_red_flags,
        "nearby_facilities": nearby_facilities,
        "first_aid_instructions": first_aid,
    }

    await notification_service.notify_emergency_worker(
        user_id=state.get("patient_id"),
        user_location={"lat": lat, "lng": lng},
        emergency_info=emergency_info,
    )

    nearest = nearby_facilities[0] if nearby_facilities else None
    message_lines = [
        "CRITICAL: Potential life-threatening condition detected.",
        "Call emergency services immediately.",
        "Tap the Nearby Hospitals button to find hospitals around you.",
    ]

    logger.warning("Emergency path triggered for patient_id=%s", state.get("patient_id"))
    return {
        **state,
        "urgency_level": "EMERGENCY",
        "is_emergency": True,
        "emergency_info": emergency_info,
        "final_report": "\n".join(message_lines),
        "next_step": "end",
        "messages": [{"role": "assistant", "content": "\n".join(message_lines)}],
    }
