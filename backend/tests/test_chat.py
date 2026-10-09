"""
Tests for chat endpoints.
Uses AsyncClient to test the non-blocking medical chat pipeline.
"""

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_chat_endpoint(client: AsyncClient):
    """
    Test basic chat functionality.
    Verifies that the AI provides a valid response and a session_id for continuity.
    """
    response = await client.post(
        "/api/v1/chat/chat",
        json={
            "messages": [
                {"role": "user", "content": "Hello, I have a fever"}
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "session_id" in data
    assert isinstance(data["session_id"], str)

@pytest.mark.asyncio
async def test_chat_empty_message(client: AsyncClient):
    """
    Test chat with empty message.
    Ensures our Pydantic validation catches empty strings and returns 422.
    """
    response = await client.post(
        "/api/v1/chat/chat",
        json={
            "messages": [
                {"role": "user", "content": ""}
            ]
        }
    )
    
    # 422 Unprocessable Entity - correctly handled by validation_exception_handler
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["type"] == "validation_error"

@pytest.mark.asyncio
async def test_symptom_analysis(client: AsyncClient):
    """
    Test symptom analysis endpoint.
    Verifies the structured analysis of symptoms and duration.
    """
    response = await client.post(
        "/api/v1/chat/analyze-symptoms",
        json={
            "symptoms": "Headache and nausea",
            "duration": "2 days"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    # Ensure the model returns structured medical analysis
    assert "urgency" in data or "analysis" in data

@pytest.mark.asyncio
async def test_chat_history(client: AsyncClient):
    """
    Test retrieving chat history using session persistence.
    """
    # 1. Create a chat session
    chat_response = await client.post(
        "/api/v1/chat/chat",
        json={
            "messages": [
                {"role": "user", "content": "Initial test message"}
            ]
        }
    )
    
    assert chat_response.status_code == 200
    session_id = chat_response.json()["session_id"]
    
    # 2. Retrieve history for that specific session
    history_response = await client.get(f"/api/v1/chat/history/{session_id}")
    
    assert history_response.status_code == 200
    history_data = history_response.json()
    assert isinstance(history_data, list)
    assert len(history_data) > 0
    # Verify the message content was saved correctly
    assert any("Initial test message" in str(msg) for msg in history_data)