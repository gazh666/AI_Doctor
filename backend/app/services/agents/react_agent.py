"""
ReAct Diagnosis Agent —— harness + loop 的统一入口。

编排流程：
  1. 用 ToolRegistry 构建工具集（harness）；用 LLM 绑定工具 + AgentLoop 构建代理；
  2. 依据 DiagnosisRequest 组装 system/human 消息（显式告知模型可用工具与手头数据）；
  3. 运行 ReAct 循环，让模型自主决定调用哪些工具、调用几次，直到信息充分；
  4. 循环收敛后，用结构化输出生成诊断/治疗方案/分诊等级，并整理成与既有
     DiagnosisResponse 兼容的结果字典。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.schemas.agents import DiagnosisRequest
from app.services.agents.harness import AgentHarness
from app.services.agents.agent_tools import build_tool_registry
from app.services.agents.loop import AgentLoop
from app.services.llm.gemini_client import gemini_client
from app.services.agents.nodes.diagnostician import DiagnosisAssessment
from app.services.agents.nodes.treatment_planner import TreatmentPlan
from app.services.agents.nodes.triage import TriageResponse
from app.services.agents.nodes.emergency_action import get_nearby_clinics


_SYSTEM_PROMPT = """\
You are a senior clinician AI assistant for a rural clinic. You autonomously gather the
evidence you need before reaching a diagnosis.

You have access to tools. Use them proactively instead of assuming:
- analyze_symptoms: structure the patient's free-text symptoms.
- analyze_lung_sound: objective auscultation of a breath-sound wav file (if a path is given).
- analyze_medical_image: interpret a medical image if provided.
- retrieve_medical_evidence: fetch grounded clinical guidelines/citations for your reasoning.
- find_nearby_clinics: locate nearby facilities in an emergency.

Rules:
- Prefer evidence over assumption; call tools when the data is available.
- If a lung-sound finding has confidence < 0.7, treat auscultation as LOW reliability and say so.
- Your output is decision support only and does NOT replace a licensed physician.
"""


class ReActDiagnosisAgent:
    def __init__(self, max_iterations: int = 8, max_tool_steps: int = 16) -> None:
        self.harness = AgentHarness(build_tool_registry())
        self.loop = AgentLoop(
            self.harness, gemini_client,
            max_iterations=max_iterations, max_tool_steps=max_tool_steps,
        )

    # ------------------------------------------------------------------
    def _build_human_prompt(self, request: DiagnosisRequest,
                            image_analysis: Optional[Dict[str, Any]]) -> str:
        lines = [
            f"Primary complaint: {request.symptoms}",
            f"Age: {request.age if request.age is not None else 'Unknown'}",
            f"Gender: {request.gender or 'Unknown'}",
            f"Medical history: {request.medical_history or 'None reported'}",
            f"Vitals: {request.vitals.model_dump() if request.vitals else 'Not provided'}",
        ]
        if request.lung_sound_path:
            lines.append(
                f"Breath-sound audio available at: {request.lung_sound_path} "
                f"(call analyze_lung_sound on this path)."
            )
        if request.lung_sound_result:
            lines.append(
                f"Pre-computed lung sound result: {json.dumps(request.lung_sound_result, ensure_ascii=False)}"
            )
        if image_analysis:
            lines.append(
                f"Pre-computed image analysis: {json.dumps(image_analysis, ensure_ascii=False)}"
            )
        lines.append(
            "Gather the clinical evidence you need via tools, then provide the final assessment."
        )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    def _build_diagnosis_context(self, request: DiagnosisRequest,
                                 image_analysis: Optional[Dict[str, Any]]) -> str:
        obs = self.harness.observations
        ctx = (
            f"Patient Age: {request.age if request.age is not None else 'Unknown'}\n"
            f"Gender: {request.gender or 'Unknown'}\n"
            f"Symptoms: {request.symptoms}\n"
            f"Vitals: {request.vitals.model_dump() if request.vitals else 'Stable/Not provided'}\n"
        )
        symptoms = obs.get("analyze_symptoms")
        if symptoms:
            ctx += f"[Structured Symptoms]: {json.dumps(symptoms, ensure_ascii=False)}\n"

        if image_analysis:
            ctx += f"[Image Findings]: {json.dumps(image_analysis, ensure_ascii=False)}\n"

        lung = obs.get("analyze_lung_sound") or request.lung_sound_result
        if lung:
            ctx += (
                f"[Lung Sound Auscultation]: {lung.get('label', 'unknown')} "
                f"(confidence={float(lung.get('confidence', 0)):.2f})\n"
            )

        citations = obs.get("retrieve_medical_evidence") or []
        if citations:
            rag_text = "\n".join(
                f"[{c.get('rank', i + 1)}] {c.get('title')}\nExcerpt: {c.get('excerpt')}"
                for i, c in enumerate(citations)
            )
        else:
            rag_text = "No matching medical source was found."
        ctx += f"\n[Medical Evidence]:\n{rag_text}\n"

        if (obs.get("analyze_lung_sound") or request.lung_sound_result):
            conf = float((obs.get("analyze_lung_sound") or request.lung_sound_result or {}).get("confidence", 0))
            if conf < 0.7:
                ctx += "\nNote: auscultation reliability is LOW (confidence<0.7); flag for clinician review.\n"
        return ctx

    # ------------------------------------------------------------------
    async def run(self, request: DiagnosisRequest,
                  image_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=self._build_human_prompt(request, image_analysis)),
        ]

        final_messages, steps = await self.loop.run(messages)

        # 结构化产出（保证与既有 DiagnosisResponse 契约一致）
        diagnosis: DiagnosisAssessment = await gemini_client.generate_structured(
            prompt=self._build_diagnosis_context(request, image_analysis),
            response_model=DiagnosisAssessment,
        )

        treatment: TreatmentPlan = await gemini_client.generate_structured(
            prompt=(
                f"Primary Diagnosis: {diagnosis.primary_diagnosis}\n"
                f"Confidence: {diagnosis.confidence}\n"
                f"Patient Age/Gender: {request.age}, {request.gender}\n"
                f"Urgency: ROUTINE\n"
                "Design a rural-optimized treatment plan (essential medicines, home care, red flags)."
            ),
            response_model=TreatmentPlan,
        )

        triage: TriageResponse = await gemini_client.generate_structured(
            prompt=(
                f"Assess urgency of this case:\nSymptoms: {request.symptoms}\n"
                f"Structured: {json.dumps(self.harness.observations.get('analyze_symptoms', {}), ensure_ascii=False)}\n"
                "Return urgency one of EMERGENCY/URGENT/ROUTINE/SELF-CARE."
            ),
            response_model=TriageResponse,
        )

        citations = self.harness.observations.get("retrieve_medical_evidence") or []
        urgency = triage.urgency
        is_emergency = urgency == "EMERGENCY"

        emergency_info = None
        if is_emergency and request.user_location:
            clinics = get_nearby_clinics(
                lat=request.user_location.lat, lng=request.user_location.lng, limit=3,
            )
            emergency_info = {
                "status": "CRITICAL",
                "red_flags": triage.red_flags,
                "nearby_facilities": clinics,
            }

        workflow_steps = [f"tool:{s['tool']}" for s in steps]
        final_report = self._build_report(request, diagnosis, treatment, urgency)

        return {
            "diagnosis": diagnosis,
            "treatment_plan": treatment,
            "urgency_level": urgency,
            "citations": citations,
            "is_grounded_in_rag": bool(citations),
            "final_report": final_report,
            "workflow_steps": workflow_steps,
            "is_emergency": is_emergency,
            "emergency_info": emergency_info,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _build_report(request: DiagnosisRequest, diagnosis: DiagnosisAssessment,
                      treatment: TreatmentPlan, urgency: str) -> str:
        lines = [
            "# MEDICAL CONSULTATION SUMMARY",
            "",
            f"- **Age:** {request.age if request.age is not None else 'N/A'}",
            f"- **Gender:** {request.gender or 'N/A'}",
            f"- **Triage Urgency:** {urgency}",
            "",
            "### Chief Complaint",
            f"> {request.symptoms}",
            "",
            "### Assessment & Diagnosis",
            f"**Primary Diagnosis:** {diagnosis.primary_diagnosis}",
            f"**Confidence:** {int(diagnosis.confidence * 100)}%",
            f"**Differential:** {', '.join(diagnosis.differential_diagnoses)}",
            "",
            "### Treatment Plan",
        ]
        if treatment.immediate_care:
            lines.append("**Immediate Actions:** " + ", ".join(treatment.immediate_care))
        for m in treatment.medications:
            lines.append(f"  - {m.name} ({m.dosage} {m.frequency})")
        lines.append(f"**Follow-up:** {treatment.follow_up.timing}")
        lines.append("")
        lines.append("*Disclaimer: AI-generated summary for decision support. Not a replacement for professional medical judgment.*")
        return "\n".join(lines)