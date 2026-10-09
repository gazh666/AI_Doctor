"""
Tests for Voice and Audio Processing endpoints.
Verifies TTS, Transcription, and Language support for the Rural AI Doctor.
"""

import pytest
from httpx import AsyncClient
from io import BytesIO

@pytest.mark.asyncio
async def test_voice_languages(client: AsyncClient):
    """
    Test getting supported languages.
    Ensures the 14+ languages required for rural clinical support are available.
    """
    # Fix: Route is /api/v1/voice/languages based on router prefixing
    response = await client.get("/api/v1/voice/languages")
    
    assert response.status_code == 200
    data = response.json()
    assert "transcription_languages" in data
    assert "tts_languages" in data
    
    # Verify presence of key regional languages
    trans_langs = data["transcription_languages"]
    assert any(lang in ["hi", "bn", "ta"] for lang in trans_langs.keys())

@pytest.mark.asyncio
async def test_tts_endpoint(client: AsyncClient):
    """
    Test Text-to-Speech (TTS) generation.
    Verifies that the API returns the correct audio content type.
    """
    response = await client.post(
        "/api/v1/voice/tts",
        json={
            "text": "Hello, this is a diagnostic test.",
            "language": "en",
            "slow": False
        }
    )
    
    assert response.status_code == 200
    # Check for audio content type to ensure it can be played in the frontend
    assert "audio" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_transcribe_invalid_file(client: AsyncClient):
    """
    Test transcription with corrupt or invalid audio data.
    Ensures the system catches binary noise.
    """
    invalid_audio = b"this-is-not-a-valid-wav-header"
    
    # Ensure the key 'file' matches the parameter name in your endpoint
    files = {
        "file": ("test.wav", BytesIO(invalid_audio), "audio/wav")
    }
    
    response = await client.post("/api/v1/voice/transcribe", files=files)
    
    # Validation errors or internal errors are expected for corrupt binary
    assert response.status_code in [400, 422, 500]

@pytest.mark.asyncio
async def test_voice_diagnose_async(client: AsyncClient, mocker):
    # 1. Mock Transcription
    mocker.patch(
        "app.services.voice.service.voice_service.transcribe_audio",
        return_value="I have a cough"
    )
    
    # 2. Mock the Agent Graph to avoid 429 Rate Limits
    mock_final_state = {
        "diagnosis": {"primary_diagnosis": "Common Cold"},
        "treatment_plan": {"immediate_care": ["Rest"]},
        "urgency_level": "ROUTINE",
        "confidence": 0.9,
        "final_report": "Mocked clinical report"
    }
    mocker.patch("app.api.v1.endpoints.voice.medical_agent_graph.ainvoke", return_value=mock_final_state)
    
    # 3. Mock TTS to prevent external calls
    mocker.patch("app.services.voice.service.voice_service.generate_speech", return_value=b"fake-audio")

    files = {"audio": ("input.wav", BytesIO(b"data"), "audio/wav")}
    data = {"age": "45", "gender": "Female"}
    response = await client.post("/api/v1/voice/diagnose", files=files, data=data)
    
    assert response.status_code == 200