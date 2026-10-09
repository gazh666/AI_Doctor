import io
import logging
import asyncio
from typing import Dict, Optional, Generator, AsyncGenerator
from gtts import gTTS
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class TTSService:

    SUPPORTED_LANGUAGES = {
        "en": "English", "hi": "Hindi", "es": "Spanish",
        "zh": "Chinese", "fr": "French", "de": "German",
        "ja": "Japanese", "ko": "Korean", "pt": "Portuguese",
        "ru": "Russian", "ar": "Arabic", "ta": "Tamil",
        "te": "Telugu", "bn": "Bengali"
    }

    def __init__(self):
        
        self.executor = ThreadPoolExecutor(max_workers=3)

    async def text_to_speech_async(
        self, 
        text: str, 
        language: str = "en", 
        slow: bool = False
    ) -> bytes:
        """
        Non-blocking wrapper for gTTS generation.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self._generate_audio, 
            text, language, slow
        )

    def _generate_audio(self, text: str, language: str, slow: bool) -> bytes:
        """Internal synchronous generator."""
        try:
            tts = gTTS(text=text, lang=language, slow=slow, lang_check=False)
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            return audio_io.getvalue()
        except Exception as e:
            logger.error(f"gTTS Error: {e}")
            raise Exception(f"Failed to generate speech: {str(e)}")

    async def stream_speech(
        self, 
        text: str, 
        language: str = "en", 
        chunk_size: int = 1024
    ) -> AsyncGenerator[bytes, None]:
     
        audio_data = await self.text_to_speech_async(text, language)
        audio_io = io.BytesIO(audio_data)
        
        while True:
            chunk = audio_io.read(chunk_size)
            if not chunk:
                break
            yield chunk
            await asyncio.sleep(0)

    def get_supported_languages(self) -> Dict[str, str]:
    
        return self.SUPPORTED_LANGUAGES


tts_service = TTSService()