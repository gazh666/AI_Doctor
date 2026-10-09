import io
import logging
from typing import Optional, Tuple
import numpy as np

# Configuration & Logging
logger = logging.getLogger(__name__)

class AudioUtils:
    """
    Advanced Audio Utilities for Rural AI Doctor.
    Standardizes patient recordings for optimal AI transcription and 
    cleans background noise typical in rural settings.
    """
    
    @staticmethod
    def get_audio_duration(audio_data: bytes) -> float:
        """Get duration of audio in seconds safely."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            return len(audio) / 1000.0
        except Exception as e:
            logger.error(f"Duration extraction failed: {e}")
            return 0.0

    @staticmethod
    def validate_audio(audio_data: bytes) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive validation of the incoming patient recording.
        Checks for file size, empty headers, and length constraints.
        """
        # 1. Size validation: 25MB limit
        if len(audio_data) > 25 * 1024 * 1024:
            return False, "Audio file is too large (max 25MB)."
        
        # 2. Header validation
        if len(audio_data) < 2000: 
            return False, "Audio file is too small or empty."

        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            duration = len(audio) / 1000.0
            
            # 3. Length validation
            if duration > 600:
                return False, "Recording exceeds 10-minute limit."
            if duration < 0.5:
                return False, "Recording is too short (min 0.5s)."
                
            return True, None
        except Exception as e:
            return False, f"Unsupported or corrupt audio format: {str(e)}"

    @staticmethod
    def preprocess_for_medical_ai(audio_data: bytes) -> bytes:
        """
        Main preprocessing pipeline:
        1. Standardization (16kHz, Mono, 16-bit PCM)
        2. Advanced Noise Reduction (noisereduce)
        3. Frequency Filtering (High/Low pass)
        4. Normalization
        """
        try:
            from pydub import AudioSegment
            import noisereduce as nr
          
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
            
        
            samples = np.array(audio.get_array_of_samples()).astype(np.float32)
            rate = audio.frame_rate
            
          
            reduced_noise = nr.reduce_noise(y=samples, sr=rate, prop_decrease=0.8)
            
            # Reconstruct AudioSegment from processed samples
            audio = audio._spawn(reduced_noise.astype(np.int16).tobytes())

          
            audio = audio.high_pass_filter(100) 
           
            audio = audio.low_pass_filter(3500) 
            
            
            audio = audio.normalize(headroom=0.1)
            
            #  Export to standardized WAV
            output_io = io.BytesIO()
            audio.export(output_io, format="wav", codec="pcm_s16le")
            return output_io.getvalue()

        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            # Fallback: If noise reduction fails, return original data to avoid crashing the request
            return audio_data

audio_utils = AudioUtils()