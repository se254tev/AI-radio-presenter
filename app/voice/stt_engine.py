import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class STTEngine:
    """Optional speech-to-text interface for future voice-driven features."""

    def __init__(self, provider: str = "mock"):
        self.provider = provider
        self.logger = logging.getLogger(__name__)

    async def transcribe(self, audio_data: bytes, language: str = "english") -> Dict[str, Any]:
        """Transcribe audio data to text."""
        self.logger.info(f"Transcribing audio in {language} using {self.provider}")
        return {
            "transcription": "[mock transcription]",
            "language": language,
            "provider": self.provider,
        }
