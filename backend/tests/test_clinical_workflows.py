from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_current_active_user
from app.db.models import AIDecisionAudit, User
from app.db.session import get_db
from app.main import app


class AsyncSessionWrapper:
    def __init__(self, sync_session):
        self._session = sync_session

    async def execute(self, *args, **kwargs):
        return self._session.execute(*args, **kwargs)

    async def commit(self):
        self._session.commit()

    async def refresh(self, instance):
        self._session.refresh(instance)

    async def flush(self):
        self._session.flush()

    def add(self, instance):
        self._session.add(instance)


@pytest.fixture
def current_user(db_session) -> Generator[User, None, None]:
    user = User(
        email=f"tester_{datetime.now(timezone.utc).timestamp()}@example.com",
        hashed_password="hashed",
        full_name="Test Clinician",
        role="doctor",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user


@pytest.fixture
async def api_client(db_session, current_user: User) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield AsyncSessionWrapper(db_session)

    async def override_current_user():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_triage_assess_and_escalate(api_client: AsyncClient):
    assess_payload = {
        "symptoms": "Severe chest pain and shortness of breath",
        "age": 56,
        "risk_factors": ["hypertension"],
        "vitals": {"spo2": 89, "systolic_bp": 190, "diastolic_bp": 125},
    }
    assess_response = await api_client.post("/api/v1/triage/assess", json=assess_payload)
    assert assess_response.status_code == 201

    assess_data = assess_response.json()
    assert assess_data["urgency_level"] == "emergency"
    assert len(assess_data["red_flags"]) > 0

    escalate_response = await api_client.post(
        "/api/v1/triage/escalate",
        json={"assessment_id": assess_data["assessment_id"], "reason": "Critical signs observed at village clinic"},
    )
    assert escalate_response.status_code == 200
    assert escalate_response.json()["status"] == "escalated"


@pytest.mark.asyncio
async def test_followup_status_transition(api_client: AsyncClient):
    due_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create_response = await api_client.post(
        "/api/v1/followups/schedule",
        json={"due_at": due_at, "channel": "sms", "reminder_enabled": True, "notes": "Recheck symptoms"},
    )
    assert create_response.status_code == 201
    followup = create_response.json()

    status_response = await api_client.patch(
        f"/api/v1/followups/{followup['id']}/status",
        json={"status": "completed", "outcome": "Patient improved"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_medication_safety_critical_allergy(api_client: AsyncClient):
    response = await api_client.post(
        "/api/v1/medications/check-interactions",
        json={
            "medications": ["Paracetamol", "Aspirin"],
            "allergies": ["paracetamol"],
            "conditions": [],
            "pregnant": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "critical"
    assert len(data["contraindications"]) > 0


@pytest.mark.asyncio
async def test_sync_conflict_and_merge_resolution(api_client: AsyncClient):
    now = datetime.now(timezone.utc)

    first_push = await api_client.post(
        "/api/v1/sync/push",
        json={
            "device_id": "device-001",
            "records": [
                {
                    "entity_type": "triage",
                    "entity_id": "triage-123",
                    "operation": "update",
                    "payload": {"severity": "urgent"},
                    "client_updated_at": now.isoformat(),
                }
            ],
        },
    )
    assert first_push.status_code == 200
    assert first_push.json()["accepted"] == 1

    stale_time = (now - timedelta(hours=1)).isoformat()
    second_push = await api_client.post(
        "/api/v1/sync/push",
        json={
            "device_id": "device-001",
            "records": [
                {
                    "entity_type": "triage",
                    "entity_id": "triage-123",
                    "operation": "update",
                    "payload": {"severity": "routine"},
                    "client_updated_at": stale_time,
                }
            ],
        },
    )
    assert second_push.status_code == 200
    second_data = second_push.json()
    assert second_data["conflicts"] == 1

    conflict_event_id = second_data["results"][0]["sync_event_id"]

    bad_resolve = await api_client.post(
        "/api/v1/sync/conflicts/resolve",
        json={"conflict_event_id": conflict_event_id, "strategy": "merge"},
    )
    assert bad_resolve.status_code == 400

    good_resolve = await api_client.post(
        "/api/v1/sync/conflicts/resolve",
        json={
            "conflict_event_id": conflict_event_id,
            "strategy": "merge",
            "merged_payload": {"severity": "urgent", "note": "merged"},
        },
    )
    assert good_resolve.status_code == 200
    assert good_resolve.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_audit_feedback_override_edge_case(api_client: AsyncClient, db_session, current_user: User, monkeypatch):
    from app.api.v1.endpoints import chat as chat_endpoint

    monkeypatch.setattr(chat_endpoint.gemini_client, "chat", AsyncMock(return_value="Mock answer"))

    chat_response = await api_client.post(
        "/api/v1/chat/chat",
        json={"messages": [{"role": "user", "content": "I have cough"}]},
    )
    assert chat_response.status_code == 200
    session_id = chat_response.json()["session_id"]

    decision_response = await api_client.get(f"/api/v1/audit/decision/{session_id}")
    assert decision_response.status_code == 200
    decisions = decision_response.json()
    assert len(decisions) >= 1

    db_session.add(
        AIDecisionAudit(
            user_id=current_user.id,
            session_id="manual-session",
            source_endpoint="/api/v1/test",
            decision_type="triage",
            input_summary="input",
            output_summary="output",
            model_name="gemini-test",
        )
    )
    db_session.commit()

    recent = db_session.query(AIDecisionAudit).order_by(AIDecisionAudit.id.desc()).first()
    missing_feedback = await api_client.post(
        "/api/v1/audit/feedback",
        json={"audit_id": 999999, "override_applied": True, "override_reason": "manual correction"},
    )
    assert missing_feedback.status_code == 404

    ok_feedback = await api_client.post(
        "/api/v1/audit/feedback",
        json={
            "audit_id": recent.id,
            "override_applied": True,
            "override_reason": "Doctor override",
            "clinician_feedback": "Initial recommendation was too conservative",
        },
    )
    assert ok_feedback.status_code == 200
    assert ok_feedback.json()["updated"] is True
