from typing import List, Dict, Any
from app.services.agents.state import AgentState

def format_section(title: str, content: List[str]) -> str:
    """Helper to maintain consistent professional formatting."""
    if not content:
        return ""
    header = f"### {title}\n"
    body = "\n".join(content)
    return f"{header}{body}\n\n"

async def report_generator_node(state: AgentState) -> AgentState:
    triage = state.get('triage_result', {})
    symptoms = state.get('symptom_analysis', {})
    diagnosis = state.get('diagnosis', {})
    treatment = state.get('treatment_plan', {})
    vision = state.get('image_analysis', {})
    lung_sound = state.get('lung_sound_result', {})
    
    #  Build Markdown Sections
    report_parts = []
    
    # Header & Patient Overview
    report_parts.append("# MEDICAL CONSULTATION SUMMARY\n")
    patient_info = [
        f"**Age:** {state.get('age', 'N/A')}",
        f"**Gender:** {state.get('gender', 'N/A')}",
        f"**Case ID:** {state.get('patient_id', 'REF-INTERNAL')}"
    ]
    report_parts.append(format_section("Patient Profile", patient_info))

    # Chief Complaint
    report_parts.append(format_section("Chief Complaint", [f"> {state['symptoms']}"]))

    # Clinical Analysis
    clinical_data = []
    if symptoms:
        clinical_data.append(f"- **Primary Symptoms:** {', '.join(symptoms.get('primary_symptoms', []))}")
        clinical_data.append(f"- **Duration/Onset:** {symptoms.get('duration', 'N/A')} ({symptoms.get('onset', 'N/A')})")
        clinical_data.append(f"- **Triage Urgency:** **{triage.get('urgency', 'ROUTINE')}**")
    
    if vision:
        clinical_data.append(f"- **Imaging ({vision.get('image_type', 'Vision').upper()}):** {vision.get('clinical_findings', ['Evidence detected'])[0]}")

    report_parts.append(format_section("Clinical Assessment", clinical_data))

    # Lung Sound Auscultation（呼吸音听诊结果）
    if lung_sound:
        sound_confidence = float(lung_sound.get('confidence', 0) or 0)
        sound_lines = [
            f"- **Respiratory Sound Label:** {lung_sound.get('label', 'unknown')}",
            f"- **Auscultation Confidence:** {int(sound_confidence * 100)}%",
        ]
        if sound_confidence < 0.7:
            sound_lines.append(
                "- ⚠️ **听诊可信度低：** 该呼吸音分析置信度不足，仅作辅助参考，需临床医生复核。"
            )
        report_parts.append(format_section("Lung Sound Auscultation", sound_lines))

    # Formal Diagnosis
    if diagnosis:
        diag_info = [
            f"**Primary Diagnosis:** {diagnosis.get('primary_diagnosis')}",
            f"**Confidence Level:** {int(diagnosis.get('confidence', 0) * 100)}%",
            f"**Evidence:** {', '.join(diagnosis.get('supporting_evidence', []))}"
        ]
        report_parts.append(format_section("Assessment & Diagnosis", diag_info))

    # Treatment Strategy
    if treatment:
        tx_info = []
        if treatment.get('immediate_care'):
            tx_info.append(f"**Immediate Actions:** {', '.join(treatment['immediate_care'])}")
        
        if treatment.get('medications'):
            med_list = [f"  - {m['name']} ({m['dosage']} {m['frequency']})" for m in treatment['medications']]
            tx_info.append("**Prescribed Medications:**")
            tx_info.extend(med_list)
        
        tx_info.append(f"**Follow-up:** {treatment.get('follow_up', {}).get('timing', 'As needed')}")
        report_parts.append(format_section("Treatment Plan", tx_info))

    # Safety Warnings
    if treatment and treatment.get('red_flags'):
        warnings = [f" **{flag}**" for flag in treatment['red_flags']]
        report_parts.append(format_section("Critical Warning Signs", warnings))

    # 3. Footer & Legal Disclaimer
    report_parts.append("---\n")
    report_parts.append("*Disclaimer: This is an AI-generated clinical summary for healthcare support. "
                        "Not a replacement for professional medical judgment.*")

    # 4. Final Compilation
    final_report = "".join(report_parts)
    
    print(f" Final Report Compiled ({len(final_report)} chars)")

    # 5. Return updated state
    return {
        **state,
        "final_report": final_report,
        "next_step": "end",
        "messages": [{
            "role": "assistant", 
            "content": "###  Clinical Report Ready\nYour comprehensive medical summary has been generated based on symptom analysis and clinical evidence."
        }]
    }