from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from app.services.agents.state import AgentState
from app.services.llm.gemini_client import gemini_client

class Medication(BaseModel):
    name:str
    dosage:str
    frequency:str
    duration:str
    notes:Optional[str]=None

class FollowUp(BaseModel):
    timing: str
    what_to_monitor: List[str]

class TreatmentPlan(BaseModel):
    """Structured schema for rural-optimized medical treatment."""
    immediate_care: List[str] = Field(description="Actions to take immediately")
    medications: List[Medication] = Field(default_factory=list)
    non_pharmacological: List[str] = Field(description="Non-drug interventions (rest, hydration, etc.)")
    follow_up: FollowUp
    red_flags: List[str] = Field(description="Warning signs specific to this diagnosis")
    when_to_seek_emergency: List[str] = Field(description="Specific triggers for ER visits")
    lifestyle_advice: List[str]
    referral_needed: bool
    referral_specialty: Optional[str] = None
    resource_consideration: str = Field(description="Note on how this plan adapts to rural limitations")


async def treatment_planner_node(state:AgentState)->AgentState:
    diagnosis=state.get('diagnosis',{})
    primary_dx=diagnosis.get('primary_diagnosis',"Unknown Condition")

    context_str = (
        f"Primary Diagnosis: {primary_dx}\n"
        f"Confidence Score: {diagnosis.get('confidence', 0.5)}\n"
        f"Urgency Level: {state.get('urgency_level', 'ROUTINE')}\n"
        f"Patient Age/Gender: {state.get('age', 'N/A')}, {state.get('gender', 'N/A')}\n"
        f"Medical History: {state.get('medical_history', 'None reported')}"
    )

    system_prompt = f"""You are a senior medical consultant designing treatment for rural clinics.
    
    [PATIENT DIAGNOSIS]
    {context_str}
    
    Instructions:
    - Prioritize commonly available medications (Essential Medicines List).
    - Provide clear, jargon-free instructions for home care.
    - Explicitly state 'Red Flags' that require the patient to travel to a city hospital.
    - If referral_needed is true, specify the specialty (e.g., Cardiology, Dermatology).
    """

    try:
        structured_plan: TreatmentPlan = await gemini_client.generate_structured(
            prompt=system_prompt,
            response_model=TreatmentPlan
        )
    except Exception as llm_err:
        print(f"Treatment Planner LLM Error: {llm_err}")
        fallback_plan = TreatmentPlan(
            immediate_care=[
                "Rest and stay hydrated.",
                "Monitor symptoms closely for the next 24 hours.",
            ],
            medications=[],
            non_pharmacological=[
                "Use supportive home care based on comfort and tolerance.",
            ],
            follow_up=FollowUp(
                timing="Within 24-48 hours or sooner if symptoms worsen",
                what_to_monitor=["fever", "pain", "breathing difficulty", "worsening weakness"],
            ),
            red_flags=[
                "persistent high fever",
                "severe chest pain",
                "difficulty breathing",
            ],
            when_to_seek_emergency=[
                "new confusion",
                "fainting",
                "rapidly worsening symptoms",
            ],
            lifestyle_advice=["Maintain hydration", "Avoid overexertion until recovery"],
            referral_needed=False,
            referral_specialty=None,
            resource_consideration="Fallback care plan generated because advanced planning service is temporarily unavailable.",
        )

        return {
            **state,
            "treatment_plan": fallback_plan.model_dump(),
            "next_step": "generate_report",
            "messages": [{
                "role": "assistant",
                "content": "Treatment planner fallback activated. A safe default plan has been generated.",
            }],
        }

    med_count = len(structured_plan.medications)
    plan_msg = {
        "role": "assistant",
        "content": (
            f"💊 **Treatment Plan for {primary_dx}**\n"
            f"- **Immediate Care:** {structured_plan.immediate_care[0] if structured_plan.immediate_care else 'Rest'}\n"
            f"- **Medications:** {f'{med_count} items prescribed' if med_count > 0 else 'None required'}\n"
            f"- **Referral:** {'Required to ' + structured_plan.referral_specialty if structured_plan.referral_needed else 'Not required'}"
        )
    }

    print(f"✅ Treatment Plan: {med_count} medications | Referral: {structured_plan.referral_needed}")

    return {
        **state,
        "treatment_plan": structured_plan.model_dump(),
        "next_step": "generate_report",
        "messages": [plan_msg]
    }