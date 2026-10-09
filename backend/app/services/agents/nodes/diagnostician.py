from typing import List, Optional
from pydantic import BaseModel, Field
from app.services.agents.state import AgentState
from app.services.llm.gemini_client import gemini_client
from app.services.rag.grounding import retrieve_medical_grounding
from app.services.rag.reputable_sources import retrieve_reputable_citations
from app.services.rag.source_catalog import retrieve_catalog_citations
import asyncio


def _provider_weight(provider: str) -> float:
    weights = {
        "LocalRAG": 1.0,
        "PubMed": 0.95,
        "OpenFDA": 0.9,
        "MedlinePlus": 0.85,
        "ClinicalTrials": 0.8,
    }
    return weights.get(provider, 0.75)


def _rank_citations(citations: list[dict]) -> list[dict]:
    ranked = sorted(
        citations,
        key=lambda c: float(c.get("similarity", 0.0) or 0.0) * _provider_weight(str(c.get("provider") or "")),
        reverse=True,
    )
    for idx, citation in enumerate(ranked, start=1):
        citation["rank"] = idx
    return ranked

class DiagnosisAssessment(BaseModel):
    """Structured schema for clinical diagnosis and reasoning."""
    primary_diagnosis: str = Field(description="The most likely medical condition")
    confidence: float = Field(ge=0, le=1.0, description="Confidence score between 0 and 1")
    differential_diagnoses: List[str] = Field(description="Alternative conditions considered")
    supporting_evidence: List[str] = Field(description="Clinical findings supporting the primary diagnosis")
    ruling_out: List[str] = Field(description="Conditions excluded based on evidence")
    recommended_tests: List[str] = Field(description="Follow-up diagnostic tests needed")
    reasoning: str = Field(description="Detailed clinical justification")

async def diagnostician_node(state: AgentState) -> AgentState:
    raw_text = state.get('transcription') or state.get('symptoms') or "No symptoms provided"

    analysis = state.get('symptom_analysis') or {}
    vision = state.get('image_analysis') or {}
    lung_sound = state.get('lung_sound_result') or {}

    primary_symptoms = analysis.get('primary_symptoms', [])
    if not primary_symptoms:
        primary_symptoms = [state.get('symptoms', 'No symptoms provided')]

    context_str = (
        f"Patient Age: {state.get('age', 'Unknown')}\n"
        f"Gender: {state.get('gender', 'Unknown')}\n"
        f"Primary Symptoms: {', '.join(primary_symptoms)}\n"
        f"Duration: {analysis.get('duration', 'N/A')}\n"
        f"Vitals: {state.get('vitals', 'Stable/Not provided')}\n"
    )
    
    if vision:
        context_str += (
            f"\n[Vision Findings]: {', '.join(vision.get('clinical_findings', []))}\n"
            f"[Vision Severity]: {vision.get('severity', 'N/A')}\n"
        )

    if lung_sound:
        context_str += (
            f"\n[Lung Sound Auscultation]: {lung_sound.get('label', 'unknown')} "
            f"(confidence={lung_sound.get('confidence', 0):.2f})\n"
        )

    retrieved_docs, catalog_docs, reputable_docs = await asyncio.gather(
        retrieve_medical_grounding(raw_text, top_k=3),
        retrieve_catalog_citations(raw_text, top_k=3),
        retrieve_reputable_citations(raw_text, top_k=4),
    )
    merged_citations = _rank_citations([
        *(catalog_docs or []),
        *(retrieved_docs or []),
        *(reputable_docs or []),
    ])[:8]

    if merged_citations:
        rag_text = "\n\n".join(
            [
                f"[{doc['rank']}] {doc['title']}\nExcerpt: {doc['excerpt']}"
                for doc in merged_citations
            ]
        )
    else:
        rag_text = "No matching medical source was found in the grounded knowledge base or trusted external references."


    system_prompt = f"""You are a senior clinical diagnostician. 
    Analyze the patient data to provide a structured diagnosis, integrating all available modalities.
    
    [PATIENT DATA]
    {context_str}
    
    [MEDICAL GUIDELINES (RAG)]
    {rag_text}
    
    Instructions:
    - Prioritize clinical safety and list reasonable differential diagnoses.
    - If a [Lung Sound Auscultation] finding is present, incorporate it as an objective physical sign into your reasoning.
    - If the lung sound confidence is below 0.7, you MUST explicitly state that auscultation reliability is LOW and a clinician review is required.
    - Your output is for decision support only and does NOT replace a licensed physician.
    """

    try:
        diagnosis_output: DiagnosisAssessment = await gemini_client.generate_structured(
            prompt=system_prompt,
            response_model=DiagnosisAssessment
        )
    except Exception as llm_err:
        print(f" Diagnostician LLM Error: {llm_err}")
    
        return {
            **state,
            "next_step": "treatment_planning",
            "messages": [{"role": "assistant", "content": "🚨 Diagnosis failed due to LLM error."}]
        }

  
    diag_msg = {
        "role": "assistant",
        "content": (
            f"🔬 **Clinical Diagnosis: {diagnosis_output.primary_diagnosis}**\n"
            f"**Confidence:** {int(diagnosis_output.confidence * 100)}%\n"
            f"**Evidence:** {diagnosis_output.supporting_evidence[0] if diagnosis_output.supporting_evidence else 'Clinical presentation'}\n"
            f"**Recommended Tests:** {', '.join(diagnosis_output.recommended_tests[:2])}"
        )
    }

    print(f"✅ Diagnosis: {diagnosis_output.primary_diagnosis} ({diagnosis_output.confidence})")

    return {
        **state,
        "diagnosis": diagnosis_output.model_dump(),
        "rag_context": merged_citations,
        "confidence": diagnosis_output.confidence,
        "next_step": "treatment_planning",
        "messages": [diag_msg]
    }