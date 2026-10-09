"""
Symptom Analyzer Agent - Extracts and structures symptom data
Uses Pydantic Structured Outputs and LangGraph 0.2+ State Management.
"""

from typing import List, Literal

from pydantic import BaseModel, Field

from app.services.agents.state import AgentState
from app.services.llm.gemini_client import gemini_client


class SymptomExtraction(BaseModel):
    """Structured schema for medical symptom extraction."""

    primary_symptoms: List[str] = Field(description="The main medical complaints reported by the patient")
    duration: str = Field(description="How long symptoms have been present (e.g., '3 days')")
    severity: Literal["mild", "moderate", "severe", "unknown"]
    associated_symptoms: List[str] = Field(default_factory=list, description="Secondary symptoms mentioned")
    aggravating_factors: List[str] = Field(default_factory=list, description="Things that make the pain or symptom worse")
    relieving_factors: List[str] = Field(default_factory=list, description="Things that provide relief")
    onset: Literal["sudden", "gradual", "unknown"]
    pattern: Literal["constant", "intermittent", "worsening", "improving", "unknown"]
    red_flags: List[str] = Field(
        default_factory=list,
        description="Immediate danger signs such as chest pain, breathing difficulty, severe bleeding, stroke signs",
    )
    emergency_reason: str = Field(default="", description="Short explanation if emergency escalation is required")


async def symptom_analyzer_node(state: AgentState) -> AgentState:
    """
    Symptom Analyzer: Converts raw text into clinical data points.
    This node is essential for mapping patient lay-language to medical RAG search terms.
    """
    patient_info = (
        f"Raw Symptoms: {state['symptoms']}\n"
        f"Age: {state.get('age', 'Unknown')}\n"
        f"Gender: {state.get('gender', 'Unknown')}"
    )

    system_prompt = f"""You are a specialized medical assistant. Your goal is to convert
    raw patient descriptions into structured clinical data for a doctor's review.

    Patient Context:
    {patient_info}

    Red Flag Triage Rules:
    - Flag emergencies when there is chest pain, breathing difficulty, severe bleeding,
      stroke-like symptoms, seizures, collapse, or sudden confusion.
    - Add each detected critical sign to red_flags.
    - If no red flags are present, keep red_flags empty and emergency_reason blank.

    Extract the information precisely. If a specific field is not mentioned by the patient,
    mark it as 'unknown' or provide an empty list for arrays.
    """

    try:
        extracted_data: SymptomExtraction = await gemini_client.generate_structured(
            prompt=system_prompt,
            response_model=SymptomExtraction,
        )
    except Exception as exc:
        print(f"Symptom Analysis Node Error: {exc}")
        return {
            **state,
            "next_step": "diagnosis",
            "is_emergency": False,
            "emergency_info": None,
            "messages": [
                {
                    "role": "assistant",
                    "content": "Symptom analysis encountered an error. Proceeding with raw data.",
                }
            ],
        }

    has_red_flags = len(extracted_data.red_flags) > 0
    next_node = "diagnosis"
    if state.get("has_image"):
        next_node = "image_analysis"
    if has_red_flags:
        next_node = "emergency_action"

    analysis_msg = {
        "role": "assistant",
        "content": (
            "Symptom Analysis Complete\n"
            f"- Primary: {', '.join(extracted_data.primary_symptoms) if extracted_data.primary_symptoms else 'None identified'}\n"
            f"- Duration: {extracted_data.duration}\n"
            f"- Severity: {extracted_data.severity.capitalize()}\n"
            f"- Onset: {extracted_data.onset.capitalize()}\n"
            f"- Red Flags: {', '.join(extracted_data.red_flags) if extracted_data.red_flags else 'None detected'}"
        ),
    }

    print(f"Symptom Analysis: {len(extracted_data.primary_symptoms)} symptoms identified")

    return {
        **state,
        "symptom_analysis": extracted_data.model_dump(),
        "is_emergency": has_red_flags,
        "emergency_info": (
            {
                "status": "CRITICAL",
                "red_flags": extracted_data.red_flags,
                "reason": extracted_data.emergency_reason,
            }
            if has_red_flags
            else None
        ),
        "next_step": next_node,
        "messages": [analysis_msg],
    }
