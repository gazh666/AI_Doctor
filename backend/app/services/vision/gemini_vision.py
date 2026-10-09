
from google import genai
from app.core.config import settings
from typing import Dict, List, Optional
import base64
from pathlib import Path
from google.genai import types

class GeminiVisionService:
    def __init__(self):
        self.model_name ="gemini-3.1-flash-lite-preview"
        self.client = None

    def _get_client(self):
        if self.client is not None:
            return self.client
        if not settings.GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY is not configured")
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        return self.client
    
    async def analyze_medical_image(
    self,
    image_data: bytes,
    image_type: str,
    filename: Optional[str] = None,  # <--- ADD THIS LINE
    additional_context: Optional[str] = None
) -> Dict:
        """
        Analyze medical image using Gemini Vision
        
        Args:
            image_data: Raw image bytes
            image_type: Type of image (xray, ct_scan, skin_lesion, etc.)
            additional_context: Optional patient symptoms/history
        
        Returns:
            Dict with analysis results
        """
        
        client = self._get_client()
        
        # Create prompt based on image type
        prompt = self._create_analysis_prompt(image_type, additional_context)
        
        config = types.GenerateContentConfig(
            temperature=0.1, 
            max_output_tokens=2048,
            top_p=0.95
        )

        contents = [
            types.Part.from_text(text=prompt), # Corrected positional argument error
            types.Part.from_bytes(
                data=image_data, 
                mime_type="image/jpeg"
            )
        ]   
        
        # Generate analysis
        response = client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config
        )
        
     
        analysis = self._parse_analysis_response(response.text, image_type)
        
        return analysis
    
    def _create_analysis_prompt(self, image_type: str, context: Optional[str]) -> str:
        """Create specialized prompt based on image type"""
        
        base_instructions = """You are an expert radiologist and medical imaging specialist.
Analyze this medical image carefully and provide a detailed assessment.

CRITICAL: Always include:
1. Overall impression
2. Specific findings with anatomical locations
3. Severity assessment (normal/mild/moderate/severe/critical)
4. Differential diagnoses (if abnormalities present)
5. Recommended follow-up or additional tests
6. Confidence level in your assessment

Be precise, use medical terminology, but also provide clear explanations."""
        
        type_specific = {
            "chest_xray": """
This is a CHEST X-RAY image.

Focus on:
- Lung fields (opacities, consolidations, infiltrates)
- Heart size and silhouette
- Pleural spaces (effusions, pneumothorax)
- Bony structures
- Mediastinum
- Diaphragm position

Common conditions to evaluate:
- Pneumonia, tuberculosis, COPD, heart failure, lung cancer, pneumothorax
""",
            "skin_lesion": """
This is a SKIN LESION image.

Evaluate using ABCDE criteria:
- Asymmetry
- Border irregularity
- Color variation
- Diameter
- Evolution/Elevation

Consider:
- Melanoma risk factors
- Benign vs malignant characteristics
- Need for biopsy
""",
            "ct_scan": """
This is a CT SCAN image.

Provide detailed analysis of:
- Anatomical structures visible
- Abnormal findings
- Hounsfield unit considerations
- Slice-specific observations
""",
            "mri": """
This is an MRI image.

Analyze:
- Tissue characteristics
- Signal intensities
- Anatomical abnormalities
- Lesion characteristics if present
"""
        }
        
        prompt = base_instructions + "\n\n"
        prompt += type_specific.get(image_type, "Analyze this medical image in detail.")
        
        if context:
            prompt += f"\n\nAdditional Context:\n{context}"
        
        prompt += "\n\nProvide your analysis in a structured format."
        
        return prompt
    
    def _parse_analysis_response(self, response_text: str, image_type: str) -> Dict:
        """Parse AI response into structured format"""
        
        # Extract severity
        severity = "normal"
        response_lower = response_text.lower()
        
        if any(word in response_lower for word in ["critical", "emergency", "urgent"]):
            severity = "critical"
        elif "severe" in response_lower:
            severity = "severe"
        elif "moderate" in response_lower:
            severity = "moderate"
        elif "mild" in response_lower:
            severity = "mild"
        elif "normal" in response_lower or "no abnormalities" in response_lower:
            severity = "normal"
        
        # Extract confidence (simple heuristic)
        confidence = 0.0
        if "high confidence" in response_lower or "confident" in response_lower:
            confidence = 0.9
        elif "moderate confidence" in response_lower:
            confidence = 0.7
        elif "low confidence" in response_lower or "uncertain" in response_lower:
            confidence = 0.5
        else:
            confidence = 0.8  # default
        
        return {
            "full_analysis": response_text,
            "severity": severity,
            "confidence": confidence,
            "image_type": image_type,
            "findings_summary": self._extract_findings(response_text),
            "recommendations": self._extract_recommendations(response_text)
        }
    
    def _extract_findings(self, text: str) -> str:
        """Extract key findings from analysis"""
        # Simple extraction - look for "findings" section
        lines = text.split('\n')
        findings = []
        capture = False
        
        for line in lines:
            if 'finding' in line.lower() or 'observation' in line.lower():
                capture = True
                continue
            if capture and line.strip():
                if line.strip().startswith(('-', '•', '*', '1', '2', '3')):
                    findings.append(line.strip())
            if 'recommendation' in line.lower() or 'impression' in line.lower():
                break
        
        return '\n'.join(findings[:5]) if findings else "See full analysis"
    
    def _extract_recommendations(self, text: str) -> str:
        """Extract recommendations from analysis"""
        lines = text.split('\n')
        recommendations = []
        capture = False
        
        for line in lines:
            if 'recommend' in line.lower() or 'follow-up' in line.lower():
                capture = True
                continue
            if capture and line.strip():
                if line.strip().startswith(('-', '•', '*', '1', '2', '3')):
                    recommendations.append(line.strip())
        
        return '\n'.join(recommendations[:5]) if recommendations else "Consult with physician"


gemini_vision = GeminiVisionService()