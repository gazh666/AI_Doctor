from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VitalSigns(BaseModel):
    temperature: Optional[float] = Field(None, description="Temperature in Fahrenheit")
    blood_pressure: Optional[str] = Field(None, example="120/80")
    heart_rate: Optional[int] = Field(None, description="Beats per minute")
    oxygen_saturation: Optional[int] = Field(None, ge=0, le=100)


class GeoLocation(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class MedicationSchema(BaseModel):
    name: str
    dosage: str
    frequency: str
    duration: str
    notes: Optional[str] = None


class TreatmentPlanSchema(BaseModel):
    immediate_care: List[str] = Field(default_factory=list)
    medications: List[MedicationSchema] = Field(default_factory=list)
    non_pharmacological: List[str] = Field(default_factory=list)
    follow_up: Dict[str, Any] = Field(default_factory=dict)
    red_flags: List[str] = Field(default_factory=list)
    referral_needed: bool = False


class SourceCitation(BaseModel):
    id: int
    rank: int
    title: str
    provider: Optional[str] = None
    source: Optional[str] = None
    excerpt: str
    similarity: float = 0.0
    evidence_level: Optional[str] = None
    published_at: Optional[str] = None
    last_verified_at: Optional[str] = None


class DiagnosisRequest(BaseModel):
    symptoms: str = Field(..., min_length=5, description="Raw symptoms description from the patient")
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = Field(None)
    medical_history: Optional[str] = Field(None)
    vitals: Optional[VitalSigns] = Field(None)
    image_analysis_id: Optional[int] = Field(None, description="Optional link to pre-processed vision analysis")
    lung_sound_path: Optional[str] = Field(None, description="肺部呼吸音音频存储路径（可选）")
    lung_sound_result: Optional[Dict[str, Any]] = Field(None, description="肺部呼吸音推理结果（可选，传入可避免重复推理）")
    patient_id: Optional[int] = Field(None)
    user_location: Optional[GeoLocation] = Field(None, description="Latitude/longitude used for emergency facility routing")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symptoms": "Persistent dry cough and shortness of breath for 3 days",
                "age": 45,
                "gender": "Male",
                "vitals": {"temperature": 101.5, "blood_pressure": "130/85"},
                "user_location": {"lat": 28.6139, "lng": 77.2090},
            }
        }
    )

    @field_validator("gender", mode="before")
    @classmethod
    def normalize_gender(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip().lower()
        if not normalized:
            return None
        allowed = {
            "male": "Male",
            "female": "Female",
            "other": "Other",
            "prefer not to say": "Prefer not to say",
            "prefer_not_to_say": "Prefer not to say",
            "prefer-not-to-say": "Prefer not to say",
        }
        if normalized not in allowed:
            raise ValueError("gender must be one of: Male, Female, Other, Prefer not to say")
        return allowed[normalized]


class DiagnosisResponse(BaseModel):
    """Comprehensive output schema representing the final state of the agentic workflow."""

    primary_diagnosis: str = Field(..., alias="diagnosis")
    confidence: float = Field(..., ge=0, le=1.0)
    differential_diagnoses: List[str] = Field(default_factory=list)
    treatment_plan: TreatmentPlanSchema = Field(default_factory=TreatmentPlanSchema)
    urgency_level: Literal["EMERGENCY", "URGENT", "ROUTINE", "SELF-CARE"]
    final_report: str = Field(..., description="Markdown formatted clinical report")
    status: Literal["OK", "CRITICAL"] = "OK"
    emergency_info: Optional[Dict[str, Any]] = None
    workflow_steps: List[str] = Field(
        default_factory=list,
        description="Audit trail of which agents processed this request",
    )
    is_grounded_in_rag: bool = Field(
        default=False,
        description="Whether clinical guidelines were retrieved from the local knowledge base",
    )
    citations: List[SourceCitation] = Field(
        default_factory=list,
        description="Grounded source citations used to support diagnosis and treatment advice",
    )

    model_config = ConfigDict(populate_by_name=True)
