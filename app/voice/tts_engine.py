"""
TTS Engine - Text-to-Speech Voice Synthesis
Converts scripts to audio using ElevenLabs or similar service
Handles language-specific voice selection and streaming
"""
import logging
import asyncio
from dataclasses import dataclass
from typing import Any
from abc import ABC, abstractmethod
import httpx
import os
import time

logger = logging.getLogger(__name__)


@dataclass
class AudioOutput:
    """Generated audio output"""
    segment_id: str
    content: str
    duration_seconds: int
    audio_data: bytes = None  # Audio file bytes
    audio_url: str = None  # S3/CDN URL for streaming
    language: str = "english"
    voice_id: str = ""
    sample_rate: int = 24000
    format: str = "mp3"
    metadata: dict[str, Any] | None = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    @abstractmethod
    async def synthesize(self, text: str, language: str = "english") -> bytes:
        """Synthesize text to speech"""
        pass


class ElevenLabsTTS(TTSProvider):
    """
    ElevenLabs TTS Integration
    Provides high-quality AI voice synthesis with multiple voice options
    """
    
    API_BASE = "https://api.elevenlabs.io/v1"
    
    # Voice ID mappings for different languages and personalities
    VOICE_PROFILES = {
        "english": {
            "professional": "21m00Tcm4TlvDq8ikWAM",  # George
            "friendly": "EXAVITQu4vr4xnSDxMaL",      # Bella
            "energetic": "TM1b6xp-x50PA3kumNKl",     # Chris
            "calm": "iP95p4xoKVk53GO7hXrB",         # Alice
        },
        "swahili": {
            "professional": "g5CIjZEefAQXesDu2UjK",  # Swahili voice
            "friendly": "EXAVITQu4vr4xnSDxMaL",
            "energetic": "TM1b6xp-x50PA3kumNKl",
            "calm": "iP95p4xoKVk53GO7hXrB",
        }
    }
    
    def __init__(self, api_key: str, default_voice: str = "professional"):
        """
        Initialize ElevenLabs TTS
        
        Args:
            api_key: ElevenLabs API key
            default_voice: Default voice profile (professional, friendly, energetic, calm)
        """
        self.api_key = api_key
        self.default_voice = default_voice
        self.client = httpx.AsyncClient(
            headers={"xi-api-key": api_key},
            timeout=30.0
        )
        self.logger = logging.getLogger(__name__)
    
    def _get_voice_id(self, language: str = "english", mood: str = "professional") -> str:
        """Get voice ID based on language and mood"""
        voices = self.VOICE_PROFILES.get(language, self.VOICE_PROFILES["english"])
        voice_profile = mood if mood in voices else self.default_voice
        return voices.get(voice_profile, list(voices.values())[0])
    
    async def synthesize(
        self,
        text: str,
        language: str = "english",
        mood: str = "professional",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> bytes:
        """
        Synthesize text to speech
        
        Args:
            text: Text to synthesize
            language: Language code (english, swahili)
            mood: Voice mood (professional, friendly, energetic, calm)
            stability: Voice stability (0-1)
            similarity_boost: Speaker similarity boost (0-1)
        
        Returns:
            bytes: MP3 audio data
        """
        if not self.api_key:
            self.logger.warning("ElevenLabs API key not configured, returning mock audio")
            return self._generate_mock_audio(text)
        
        try:
            voice_id = self._get_voice_id(language, mood)
            
            url = f"{self.API_BASE}/text-to-speech/{voice_id}"
            
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                }
            }
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            audio_data = response.content
            self.logger.info(
                f"Synthesized {len(text)} chars of {language} audio "
                f"({len(audio_data)} bytes)"
            )
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"TTS synthesis failed: {e}")
            return self._generate_mock_audio(text)
    
    def _generate_mock_audio(self, text: str) -> bytes:
        """Generate mock MP3 audio for testing"""
        # Return a minimal valid MP3 header + silence
        # This is a valid MP3 frame header for ~1 second of silence
        mp3_header = b'\xff\xfb\x90\x00'  # Sync word + MPEG-1 Layer III, 128kbps
        duration_estimate = max(1, len(text.split()) // 150)
        # Generate ~128kbps * duration
        silence = b'\x00' * (128 * 128 * duration_estimate // 8)
        return mp3_header + silence
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class TTSEngine:
    """
    Text-to-Speech Engine
    Manages voice synthesis for broadcast
    Handles language selection and audio caching
    """
    
    def __init__(self, api_key: str, provider: str = "elevenlabs"):
        """
        Initialize TTS engine
        
        Args:
            api_key: API key for TTS provider
            provider: TTS provider (elevenlabs, google, aws)
        """
        self.api_key = api_key
        self.provider = provider
        self.tts_client = None
        self.audio_cache: dict[str, bytes] = {}
        self.logger = logging.getLogger(__name__)
        
        if provider == "elevenlabs":
            self.tts_client = ElevenLabsTTS(api_key)
        else:
            self.logger.warning(f"Unknown TTS provider: {provider}")
    
    async def generate_audio(
        self,
        segment_id: str,
        text: str,
        language: str = "english",
        mood: str = "professional",
        duration_estimate: int = 300,
    ) -> AudioOutput:
        """
        Generate audio from text
        
        Args:
            segment_id: Segment identifier
            text: Text to synthesize
            language: Language code
            mood: Voice mood
            duration_estimate: Estimated duration in seconds
        
        Returns:
            AudioOutput: Generated audio with metadata
        """
        if not self.tts_client:
            self.logger.warning("TTS client not configured")
            return self._create_mock_audio(segment_id, text, language, mood, duration_estimate)
        
        try:
            # Check cache
            cache_key = f"{segment_id}_{language}_{mood}"
            if cache_key in self.audio_cache:
                self.logger.debug(f"Using cached audio: {cache_key}")
                audio_data = self.audio_cache[cache_key]
            else:
                # Generate audio
                audio_data = await self.tts_client.synthesize(
                    text,
                    language=language,
                    mood=mood,
                    stability=0.5,
                    similarity_boost=0.75,
                )
                
                # Cache it
                self.audio_cache[cache_key] = audio_data
                self.logger.info(f"Generated and cached audio: {cache_key}")
            
            # Create audio output object
            audio = AudioOutput(
                segment_id=segment_id,
                content=text,
                duration_seconds=duration_estimate,
                audio_data=audio_data,
                language=language,
                voice_id="elevenlabs_default",
                metadata={
                    "provider": self.provider,
                    "cache_hit": cache_key in self.audio_cache,
                    "text_length": len(text),
                    "mood": mood,
                }
            )
            # Provide a reachable audio_url (placeholder S3 path or CDN in production)
            # Persist locally so it's accessible; producers can replace with S3 upload
            try:
                os.makedirs("./audio_cache", exist_ok=True)
                filename = f"{segment_id}_{int(time.time())}.mp3"
                path = os.path.join("./audio_cache", filename)
                with open(path, "wb") as fh:
                    fh.write(audio_data)
                audio.audio_url = f"file://{os.path.abspath(path)}"
            except Exception:
                audio.audio_url = f"s3://radio-ai/audio/{segment_id}.mp3"
            
            return audio
            
        except Exception as e:
            self.logger.error(f"Audio generation failed: {e}")
            return self._create_mock_audio(segment_id, text, language, mood, duration_estimate)
    
    def _create_mock_audio(
        self,
        segment_id: str,
        text: str,
        language: str,
        mood: str,
        duration_estimate: int,
    ) -> AudioOutput:
        """Create mock audio for testing"""
        mock_mp3 = b'\xff\xfb\x90\x00' + b'\x00' * 1024
        
        return AudioOutput(
            segment_id=segment_id,
            content=text,
            duration_seconds=duration_estimate,
            audio_data=mock_mp3,
            language=language,
            voice_id="mock_voice",
            metadata={
                "provider": self.provider,
                "is_mock": True,
                "text_length": len(text),
            }
        )
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get audio cache statistics"""
        total_size = sum(len(audio) for audio in self.audio_cache.values())
        return {
            "cached_items": len(self.audio_cache),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "cache_keys": list(self.audio_cache.keys()),
        }
    
    async def clear_cache(self):
        """Clear audio cache"""
        self.audio_cache.clear()
        self.logger.info("Audio cache cleared")
    
    async def close(self):
        """Close TTS engine"""
        if self.tts_client and hasattr(self.tts_client, 'close'):
            await self.tts_client.close()
        self.logger.info("TTS engine closed")


# Global TTS engine instance
tts_engine = None


def initialize_tts_engine(api_key: str = None, provider: str = "elevenlabs"):
    """Initialize global TTS engine"""
    global tts_engine
    if not api_key:
        from app.config.settings import CONFIG
        api_key = CONFIG.api.elevenlabs_key
    
    tts_engine = TTSEngine(api_key, provider=provider)
    return tts_engine


def get_tts_engine() -> TTSEngine:
    """Get global TTS engine"""
    global tts_engine
    if tts_engine is None:
        initialize_tts_engine()
    return tts_engine
