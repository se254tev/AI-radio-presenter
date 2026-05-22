"""
TTS Pipeline Service - Text-to-Speech with ElevenLabs and fallback support
"""
import logging
from typing import Optional, AsyncIterator
import asyncio

logger = logging.getLogger(__name__)


class TTSEngine:
    """Text-to-Speech service with support for multiple providers"""

    def __init__(self, elevenlabs_api_key: str = "", fallback_provider: str = "mock"):
        self.api_key = elevenlabs_api_key
        self.fallback = fallback_provider
        self._client = None
        self.default_voice_id = "default"

    async def initialize(self) -> None:
        """Initialize TTS client"""
        if not self.api_key:
            logger.warning(
                "ElevenLabs API key not set; using mock TTS provider"
            )
            return

        try:
            from elevenlabs import AsyncElevenLabs
            self._client = AsyncElevenLabs(api_key=self.api_key)
            logger.info("ElevenLabs TTS initialized")
        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabs: {e}")

    async def synthesize(self, text: str, voice_id: Optional[str] = None) -> bytes:
        """
        Synthesize text to audio bytes

        Args:
            text: Text to synthesize
            voice_id: Voice identifier (uses default if not specified)

        Returns:
            Audio bytes in MP3 format
        """
        voice_id = voice_id or self.default_voice_id

        if not self._client:
            logger.debug(f"Using mock TTS for: {text[:50]}...")
            return b"mock_audio_data"

        try:
            response = await self._client.generate(
                text=text,
                voice=voice_id,
                model="eleven_monolingual_v1",
            )
            logger.info(f"TTS synthesized: {text[:50]}...")
            return response
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return b"mock_audio_data"

    async def stream_synthesize(
        self, text: str, voice_id: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream TTS audio in chunks (useful for real-time delivery)

        Yields:
            Audio chunks
        """
        voice_id = voice_id or self.default_voice_id

        if not self._client:
            # Mock streaming for fallback
            yield b"mock_audio_chunk_1"
            yield b"mock_audio_chunk_2"
            return

        try:
            audio_data = await self.synthesize(text, voice_id)
            # Simulate streaming by yielding in chunks
            chunk_size = 4096
            for i in range(0, len(audio_data), chunk_size):
                yield audio_data[i : i + chunk_size]
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"TTS streaming failed: {e}")
            yield b"error_audio"

    async def get_status(self) -> dict:
        """Return TTS service status"""
        return {
            "provider": "elevenlabs" if self._client else "mock",
            "status": "ready",
            "fallback": self.fallback,
        }
