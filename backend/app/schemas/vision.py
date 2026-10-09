from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Any
from datetime import datetime


class ImageUploadResponse(BaseModel):
    message: str
    image_id: int
    analysis_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class ImageAnalysisRequest(BaseModel):
    image_type: str = Field(
        ..., 
        pattern="^(chest_xray|skin_lesion|ct_scan|mri|general)$",
        description="Type: chest_xray, skin_lesion, ct_scan, mri"
    )
    patient_context: Optional[str] = Field(
        None, 
        max_length=2000,
        description="Patient symptoms or relevant medical history"
    )
    enhance_image: bool = Field(True, description="Apply CLAHE enhancement before analysis")


class ImageAnalysisResponse(BaseModel):
    analysis_id: int
    image_type: str
    findings: str
    full_analysis: str
    severity: str = Field(..., pattern="^(normal|mild|moderate|severe|critical)$")
    confidence: float = Field(..., ge=0, le=1)
    recommendations: str
    metadata: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class XRayAnalysisRequest(BaseModel):
    symptoms: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = None
    medical_history: Optional[str] = None



class XRayAnalysisResponse(BaseModel):
    analysis_id: int
    analysis: str
    findings: List[str]
    severity: str
    confidence: float
    differential_diagnosis: List[str]
    recommendations: str
    urgent_flags: List[str]

    model_config = ConfigDict(from_attributes=True)