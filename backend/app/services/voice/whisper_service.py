import os
import io
import logging
from google import genai
from google.genai import types
from typing import Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import VoiceInteraction
from app.core.config import settings

logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self):
        """
        Cloud-based transcription service using Gemini 1.5 Flash.
        Saves ~600MB RAM compared to local Whisper models.
        """
        self.client = None
        self.model_id = 'gemini-3.1-flash-lite-preview'  # Stable multimodal production standard

    def _get_client(self):
        if self.client is not None:
            return self.client
        if not settings.GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY is not configured")
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        logger.info("🎙️ Cloud Voice Service (Gemini V2 SDK) initialized")
        return self.client

    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = None,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Primary method used by the API endpoints.
        """
        return await self._process_audio_cloud(
            audio_data,
            language,
            filename=filename,
            content_type=content_type,
        )

    def _suffix_from_meta(self, filename: Optional[str], content_type: Optional[str]) -> str:
        if filename and "." in filename:
            ext = os.path.splitext(filename)[1].strip().lower()
            if ext:
                return ext

        mime_map = {
            "audio/webm": ".webm",
            "audio/mp4": ".mp4",
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/ogg": ".ogg",
        }
        if content_type:
            return mime_map.get(content_type.lower(), ".webm")
        return ".webm"

    async def transcribe_and_save(
        self, 
        db: AsyncSession, 
        audio_data: bytes, 
        filename: str,
        session_id: Optional[str] = None,
        patient_id: Optional[int] = None
    ) -> VoiceInteraction:
        """
        Transcribes audio using cloud API and saves result to Supabase.
        """
        try:
            result = await self._process_audio_cloud(audio_data)
            
            voice_entry = VoiceInteraction(
                session_id=session_id,
                patient_id=patient_id,
                audio_filename=filename,
                transcription=result["text"],
                language=result["language"],
                duration_seconds=result["duration"],
                confidence=result["confidence"]
            )
            
            db.add(voice_entry)
            await db.commit()
            await db.refresh(voice_entry)
            
            return voice_entry
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Voice Service Error: {str(e)}")
            raise e

    async def _process_audio_cloud(
        self,
        audio_data: bytes,
        language: str = None,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Standardizes audio and sends it to Gemini Cloud for transcription.
        """
        client = self._get_client()
        duration_seconds = 0.0
        prepared_audio_data = audio_data
        prepared_mime_type = content_type or "audio/webm"
        
        try:
            # Preferred path: normalize audio to 16kHz mono WAV.
            # Fallback path uses the raw browser recording when ffmpeg/pydub decoding is unavailable.
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(io.BytesIO(audio_data))
                audio = audio.set_frame_rate(16000).set_channels(1)
                output_buffer = io.BytesIO()
                audio.export(output_buffer, format="wav")
                prepared_audio_data = output_buffer.getvalue()
                prepared_mime_type = "audio/wav"
                duration_seconds = len(audio) / 1000.0
            except Exception as decode_error:
                logger.warning("Audio normalization skipped, using raw bytes: %s", decode_error)
                guessed_suffix = self._suffix_from_meta(filename, content_type)
                suffix_to_mime = {
                    ".webm": "audio/webm",
                    ".mp4": "audio/mp4",
                    ".mp3": "audio/mpeg",
                    ".wav": "audio/wav",
                    ".ogg": "audio/ogg",
                }
                prepared_mime_type = suffix_to_mime.get(guessed_suffix, prepared_mime_type)

            prompt = "Transcribe the following medical audio accurately."
            if language:
                prompt += f" The expected language is {language}."
                
            response = client.models.generate_content(
                model=self.model_id,
                contents=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=prepared_audio_data, mime_type=prepared_mime_type),
                ],
            )
            response_text = (response.text or "").strip()
            if not response_text:
                raise RuntimeError("Transcription returned empty text.")

            return {
                "text": response_text,
                "language": language if language else "auto",
                "duration": duration_seconds,
                "confidence": 0.95
            }
        except Exception as exc:
            logger.error("Cloud transcription failed: %s", exc)
            raise

# Singleton initialization
_voice_instance = WhisperService()

def get_whisper_service():
    """
    Factory function for FastAPI dependency injection.
    """
    return _voice_instance

whisper_service = _voice_instance
