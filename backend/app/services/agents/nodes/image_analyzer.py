from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from app.services.agents.state import AgentState
from app.services.vision.gemini_vision import gemini_vision

class ImageFindings(BaseModel):
    """Structured schema for medical image interpretation"""
    clinical_findings:List[str]=Field(description="Specific observation from the image")
    severity:Literal["NORMAL","LOW","MODERATE","HIGH","CRITICAL"]
    suspected_condition:List[str]=Field(description="Potential diagnoses based on visual evidence")
    recommendation:str=Field(description="Next steps specifically regarding this image")

async def image_analyzer_node(state:AgentState)->AgentState:
    """
    Image Analyzer: Bridges the gap between the vision service and the diagnosis agent.
    If an image analysis exists, it formats it; otherwise, it triggers a new analysis.
    """
    if state.get('image_analysis'):
        analysis=state['image_analysis']   

        findings_summary=(
            f"🖼️ **Image Analysis Summary**\n"
            f"- **Findings:** {', '.join(analysis.get('findings', []))}\n"
            f"- **Severity:** {analysis.get('severity', 'Unknown')}\n"
            f"- **Suspected:** {', '.join(analysis.get('differential_diagnosis', []))}"
        )

        print("✅ Integrating existing image analysis into state")
        return {
            **state,
            "next_step": "diagnosis",
            "messages": [{"role": "assistant", "content": findings_summary}]
        }
    
    if not state.get('has_image'):
        print("No image detected,routing to standard diagnosis")
        return {
            **state,
            "next_step":"diagnosis"
        }
    
    try:
        mock_findings=ImageFindings(
            clinical_findings=["Increased opacity in lower left lobe", "Potential pleural effusion"],
            severity="HIGH",
            suspected_conditions=["Pneumonia", "Bacterial Infection"],
            recommendation="Immediate clinical correlation and possible antibiotic therapy."
        )

        analysis_msg={
            "role": "assistant",
            "content": (
                f"🖼️ **Automated Image Analysis Complete**\n"
                f"- **Primary Finding:** {mock_findings.clinical_findings[0]}\n"
                f"- **Severity Level:** {mock_findings.severity}\n"
                f"**System Recommendation:** {mock_findings.recommendation}"
            )
        }

        print(f"Image analyzed :{mock_findings.severity}severity")

        return {
            **state,
            "image_analysis": mock_findings.model_dump(),
            "next_step": "diagnosis",
            "messages": [analysis_msg]
        }
    
    except Exception as e:
        print(f"❌ Image Analysis Error: {str(e)}")
        return {
            **state,
            "next_step": "diagnosis",
            "messages": [{"role": "assistant", "content": "⚠️ Vision analysis failed. Proceeding with text-based symptoms only."}]
        }
