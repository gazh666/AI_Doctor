from typing import List, Literal
from pydantic import BaseModel, Field
from app.services.agents.state import AgentState
from app.services.llm.gemini_client import gemini_client

class TriageResponse(BaseModel):
    """Structured schema for Triage assessment."""
    urgency: Literal["EMERGENCY", "URGENT", "ROUTINE", "SELF-CARE"]
    red_flags: List[str] = Field(description="List of concerning symptoms or 'None'")
    reasoning: str = Field(description="Brief medical justification for the triage level")
    next_step: Literal["image_analysis", "symptom_analysis", "diagnosis"]

async def triage_node(state: AgentState) -> AgentState:
    """
    Triage Agent: Assess urgency and detect red flags.
    Replaces fragile string splitting with Pydantic validation.
    """

    patient_context = f"Symptoms: {state['symptoms']}\n"
    if state.get('age'): patient_context += f"Age: {state['age']}\n"
    if state.get('gender'): patient_context += f"Gender: {state['gender']}\n"
    if state.get('vitals'): patient_context += f"Vitals: {state['vitals']}\n"
    if state.get('medical_history'): patient_context += f"History: {state['medical_history']}\n"
    
    system_prompt = f"""You are an expert triage nurse in a rural clinic.
    Assess the urgency of the following patient case:
    
    {patient_context}
    
    Guidelines:
    - EMERGENCY: Life-threatening (chest pain, stroke symptoms, severe bleeding).
    - URGENT: High fever (>103°F), severe pain, signs of acute infection.
    - ROUTINE: Non-acute conditions.
    - SELF-CARE: Minor issues manageable at home.
    """

    try:
        structured_triage: TriageResponse = await gemini_client.generate_structured(
            prompt=system_prompt,
            response_model=TriageResponse
        )
    except Exception as e:
        print(f"Triage System Error: {e}")
        return {
            **state,
            "urgency_level": "ROUTINE",
            "next_step": "symptom_analysis",
            "messages": [{"role": "assistant", "content": " Triage system error. Proceeding with caution."}]
        }

    final_next_step = structured_triage.next_step
    if state.get('has_image') and final_next_step == "symptom_analysis":
        final_next_step = "image_analysis"

    triage_message = {
        "role": "assistant",
        "content": (
            f"🚨 **Triage Assessment: {structured_triage.urgency}**\n"
            f"**Red Flags:** {', '.join(structured_triage.red_flags) if structured_triage.red_flags else 'None'}\n"
            f"**Reasoning:** {structured_triage.reasoning}"
        )
    }

    return {
        **state,
        "triage_result": structured_triage.model_dump(),
        "urgency_level": structured_triage.urgency,
        "next_step": final_next_step,
        "messages": [triage_message]
    }