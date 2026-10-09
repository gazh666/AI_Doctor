from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GeoLocation(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    session_id: Optional[str] = None
    system_prompt: Optional[str] = None
    user_location: Optional[GeoLocation] = None


class ChatResponse(BaseModel):
    message: str
    session_id: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class SymptomAnalysisRequest(BaseModel):
    symptoms: str
    age: Optional[int] = None
    gender: Optional[str] = None


class SymptomAnalysisResponse(BaseModel):
    analysis: str
    severity: str
    possible_conditions: List[str]
    recommendations: str
