"""
Agent State Management
Defines the shared state that flows between agents
"""

from typing import TypedDict, List, Optional, Dict, Annotated, Any
from langgraph.graph.message import add_messages 
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    Shared state across all agents in the medical diagnosis workflow.
    Updated for LangGraph 0.2+ standards.
    """
    patient_id:Optional[int]
    symptoms:str
    user_location: Optional[Dict[str, float]]
    age:Optional[int]
    gender:Optional[str]
    medical_history:Optional[str]
    vitals:Optional[Dict[str,Any]]

    has_image:bool
    image_type:Optional[str]
    image_analysis:Optional[Dict[str,Any]]

    lung_sound_path:Optional[str]
    lung_sound_result:Optional[Dict[str,Any]]

    triage_result:Optional[Dict[str,Any]]
    syptom_analysis:Optional[Dict[str,Any]]
    symptom_analysis:Optional[Dict[str,Any]]
    rag_context:Optional[List[Dict[str,Any]]]
    diagnosis:Optional[Dict[str,Any]]
    treatment_plan:Optional[Dict[str,Any]]
    is_emergency: bool
    emergency_info: Optional[Dict[str, Any]]


    urgency_level:str
    next_step:Optional[str]

    messages:Annotated[List[BaseMessage],add_messages]

    final_report:Optional[str]
    confidence:float
