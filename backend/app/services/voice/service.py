"""
Unified Voice Service for Rural AI Doctor.
Orchestrates transcription and speech synthesis.
"""
import logging
from .whisper_service import whisper_service

from .tts_service import tts_service as tts_instance

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        self.tts_service = tts_instance
        self.whisper_service = whisper_service

    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = None,
        filename: str = None,
        content_type: str = None,
    ) -> str:
        
        clean_lang = None if language in ["string", ""] else language
        
        # Using the internal method from your whisper_service.py
        result = await self.whisper_service.transcribe_audio(
            audio_data,
            language=clean_lang,
            filename=filename,
            content_type=content_type,
        )
        return result.get("text", "")

    async def generate_speech(self, text: str, language: str = "en", slow: bool = False) -> bytes:
        """Generates audio bytes via gTTS."""
        return await self.tts_service.text_to_speech_async(text, language, slow)

    def get_languages(self):
        """Returns the 14+ clinical languages supported."""
        return self.tts_service.get_supported_languages()

voice_service = VoiceService()