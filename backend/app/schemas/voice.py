from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


from pydantic import  ConfigDict


class TranscriptionResponse(BaseModel):
    
    id: int 

    transcription: str 
    language: str
    confidence: float
    duration_seconds: float
    session_id: str
    created_at: datetime

  
    model_config = ConfigDict(from_attributes=True)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to convert to speech")
    language: str = Field("en", description="Language code (en, hi, es, etc.)")
    slow: bool = Field(False, description="Whether to use a slower speaking rate")


class TTSResponse(BaseModel):
    """Output for the gTTS Service."""
    message: str = "Audio generated successfully"
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None     
    language: str
    duration_estimate: float


class VoiceDiagnosisRequest(BaseModel):
    transcription_id: int
    language: str = Field("en", description="Preferred language for the audio feedback")
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: Optional[str] = None
    vitals: Optional[Dict[str, Any]] = None


class VoiceDiagnosisResponse(BaseModel):
    """The final result of the voice-driven medical assessment."""
    transcription: str
    diagnosis_result: Dict[str, Any]
    audio_response: Optional[str] = None  
    urgency_level: str 


class LiveVoiceClientEvent(BaseModel):
    type: Literal[
        "auth",
        "session.configure",
        "turn.start",
        "turn.audio_chunk",
        "turn.end",
        "ping",
    ]
    session_id: Optional[str] = None
    token: Optional[str] = None
    language: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: Optional[str] = None
    turn_id: Optional[str] = None
    audio: Optional[str] = None
    mime_type: Optional[str] = None
    timestamp: Optional[str] = None


class LiveVoiceServerEvent(BaseModel):
    type: Literal[
        "auth.ok",
        "turn.transcript",
        "turn.response",
        "turn.audio",
        "turn.error",
        "pong",
    ]
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    message: Optional[str] = None
    transcript: Optional[str] = None
    response_text: Optional[str] = None
    urgency: Optional[str] = None
    red_flags: Optional[List[str]] = None
    audio: Optional[str] = None
    mime_type: Optional[str] = None
    timestamp: Optional[str] = None
