import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app


def test_voice_live_auth_failure(mocker):
    mocker.patch(
        "app.api.v1.endpoints.voice._authenticate_ws_user",
        new=AsyncMock(return_value=None),
    )

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/voice/live") as ws:
            ws.send_json({"type": "auth", "token": "Bearer bad-token"})
            payload = ws.receive_json()
            assert payload["type"] == "turn.error"


def test_voice_live_turn_lifecycle_success(mocker):
    mock_user = SimpleNamespace(id=101, is_active=True)
    mocker.patch(
        "app.api.v1.endpoints.voice._authenticate_ws_user",
        new=AsyncMock(return_value=mock_user),
    )
    mocker.patch(
        "app.api.v1.endpoints.voice.audio_utils.validate_audio",
        return_value=(True, None),
    )
    mocker.patch(
        "app.api.v1.endpoints.voice.audio_utils.get_audio_duration",
        return_value=1.8,
    )
    mocker.patch(
        "app.services.voice.service.voice_service.transcribe_audio",
        new=AsyncMock(return_value="I have high fever and cough"),
    )
    mocker.patch(
        "app.api.v1.endpoints.voice.gemini_client.chat",
        new=AsyncMock(return_value="You should rest, hydrate, and monitor your fever."),
    )
    mocker.patch(
        "app.services.voice.service.voice_service.generate_speech",
        new=AsyncMock(return_value=b"fake-tts"),
    )
    persist_mock = AsyncMock(return_value=None)
    mocker.patch(
        "app.api.v1.endpoints.voice._persist_live_turn",
        new=persist_mock,
    )

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/voice/live") as ws:
            ws.send_json({"type": "auth", "token": "Bearer valid-token"})
            auth_ok = ws.receive_json()
            assert auth_ok["type"] == "auth.ok"

            ws.send_json(
                {
                    "type": "session.configure",
                    "language": "en",
                    "age": 41,
                    "gender": "Female",
                    "medical_history": "Hypertension",
                }
            )
            ws.send_json({"type": "turn.start", "turn_id": "turn-1"})
            ws.send_json(
                {
                    "type": "turn.audio_chunk",
                    "audio": base64.b64encode(b"fake-audio").decode("utf-8"),
                    "mime_type": "audio/webm",
                }
            )
            ws.send_json({"type": "turn.end", "turn_id": "turn-1"})

            transcript_evt = ws.receive_json()
            response_evt = ws.receive_json()
            audio_evt = ws.receive_json()

            assert transcript_evt["type"] == "turn.transcript"
            assert "fever" in transcript_evt["transcript"].lower()
            assert response_evt["type"] == "turn.response"
            assert "rest" in response_evt["response_text"].lower()
            assert audio_evt["type"] == "turn.audio"
            assert audio_evt["audio"]
            assert persist_mock.await_count == 1


def test_voice_live_empty_turn_error(mocker):
    mock_user = SimpleNamespace(id=102, is_active=True)
    mocker.patch(
        "app.api.v1.endpoints.voice._authenticate_ws_user",
        new=AsyncMock(return_value=mock_user),
    )

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/voice/live") as ws:
            ws.send_json({"type": "auth", "token": "Bearer valid-token"})
            _ = ws.receive_json()

            ws.send_json({"type": "turn.start", "turn_id": "turn-empty"})
            ws.send_json({"type": "turn.end", "turn_id": "turn-empty"})
            error_evt = ws.receive_json()

            assert error_evt["type"] == "turn.error"
            assert "No audio received" in error_evt["message"]


def test_voice_live_tts_failure_still_returns_text(mocker):
    mock_user = SimpleNamespace(id=103, is_active=True)
    mocker.patch(
        "app.api.v1.endpoints.voice._authenticate_ws_user",
        new=AsyncMock(return_value=mock_user),
    )
    mocker.patch(
        "app.api.v1.endpoints.voice.audio_utils.validate_audio",
        return_value=(True, None),
    )
    mocker.patch(
        "app.api.v1.endpoints.voice.audio_utils.get_audio_duration",
        return_value=1.1,
    )
    mocker.patch(
        "app.services.voice.service.voice_service.transcribe_audio",
        new=AsyncMock(return_value="My throat hurts"),
    )
    mocker.patch(
        "app.api.v1.endpoints.voice.gemini_client.chat",
        new=AsyncMock(return_value="Please drink warm fluids and rest your voice."),
    )
    mocker.patch(
        "app.services.voice.service.voice_service.generate_speech",
        new=AsyncMock(side_effect=RuntimeError("TTS unavailable")),
    )
    mocker.patch(
        "app.api.v1.endpoints.voice._persist_live_turn",
        new=AsyncMock(return_value=None),
    )

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/voice/live") as ws:
            ws.send_json({"type": "auth", "token": "Bearer valid-token"})
            _ = ws.receive_json()
            ws.send_json({"type": "turn.start", "turn_id": "turn-tts"})
            ws.send_json({"type": "turn.audio_chunk", "audio": base64.b64encode(b"abc").decode("utf-8")})
            ws.send_json({"type": "turn.end", "turn_id": "turn-tts"})

            evt1 = ws.receive_json()
            evt2 = ws.receive_json()
            assert evt1["type"] == "turn.transcript"
            assert evt2["type"] == "turn.response"
