"""
Tests for the Rural AI Doctor multi-agent system.
Verifies Triage, Symptom Analysis, and full diagnostic orchestration.
"""

import pytest
from httpx import AsyncClient
from app.services.agents.state import AgentState
from app.services.agents.nodes.triage import triage_node
from app.services.agents.nodes.symptom_analyzer import symptom_analyzer_node

@pytest.mark.asyncio
async def test_triage_node_emergency():
    """
    Test the Triage Node with emergency symptoms.
    Verifies that 'chest pain' correctly triggers EMERGENCY status.
    """
    state: AgentState = {
        "patient_id": None,
        "symptoms": "Severe chest pain radiating to left arm, difficulty breathing",
        "age": 50,
        "gender": "Male",
        "medical_history": None,
        "vitals": None,
        "has_image": False,
        "image_type": None,
        "image_analysis": None,
        "triage_result": None,
        "symptom_analysis": None,
        "rag_context": None,
        "diagnosis": None,
        "treatment_plan": None,
        "urgency_level": "ROUTINE",
        "next_step": None,
        "messages": [],
        "final_report": None,
        "confidence": 0.0
    }
    
    # Run the isolated triage node
    result = await triage_node(state)
    
    assert result["triage_result"] is not None
    # Verify the agent correctly identified the high urgency
    assert result["urgency_level"] in ["EMERGENCY", "URGENT"]
    assert "chest pain" in str(result["triage_result"]).lower()

@pytest.mark.asyncio
async def test_symptom_analyzer_node():
    """
    Test the Symptom Analyzer Node.
    Ensures clinical details are extracted into structured symptoms.
    """
    state: AgentState = {
        "patient_id": None,
        "symptoms": "High fever for 3 days, cough with yellow sputum, and chills",
        "age": 35,
        "gender": "Female",
        "medical_history": "Asthma",
        "vitals": None,
        "has_image": False,
        "image_type": None,
        "image_analysis": None,
        "triage_result": None,
        "symptom_analysis": None,
        "rag_context": None,
        "diagnosis": None,
        "treatment_plan": None,
        "urgency_level": "ROUTINE",
        "next_step": None,
        "messages": [],
        "final_report": None,
        "confidence": 0.0
    }
    
    result = await symptom_analyzer_node(state)
    
    assert result["symptom_analysis"] is not None
    analysis = result["symptom_analysis"]
    # Check for expected medical keys in the agent output
    assert any(key in analysis for key in ["primary_symptoms", "duration", "severity"])
    assert "fever" in str(analysis).lower()

@pytest.mark.asyncio
async def test_full_agent_diagnosis_endpoint(client: AsyncClient, sample_patient_data):
    """
    Test the complete end-to-end diagnostic API endpoint.
    Fixed: Added 'symptoms' to payload to prevent 422 Validation Error.
    """
    # Merge sample data with required symptoms field
    payload = {
        **sample_patient_data,
        "symptoms": "Persistent dry cough and mild fever for 2 days"
    }
    
    response = await client.post(
        "/api/v1/agents/diagnose",
        json=payload
    )
    
    # If this fails with 500, check the Gemini API connection or DB tables
    assert response.status_code == 200
    data = response.json()
    
    # Verify the structured response fields
    assert "diagnosis" in data
    assert "confidence" in data
    assert "urgency_level" in data
    assert "treatment_plan" in data
    
    # Ensure confidence is a float within a valid range
    assert 0.0 <= data["confidence"] <= 1.0

@pytest.mark.asyncio
async def test_agent_error_handling(client: AsyncClient):
    """
    Test agent system with invalid/empty inputs.
    Verifies that the system returns a 422 correctly.
    """
    # Providing a string for an integer field
    invalid_data = {"age": "not-a-number", "symptoms": "fever"}
    
    response = await client.post(
        "/api/v1/agents/diagnose",
        json=invalid_data
    )
    
    assert response.status_code == 422
    # Ensure the error structure matches our custom error handler
    assert "detail" in response.json() or "error" in response.json()