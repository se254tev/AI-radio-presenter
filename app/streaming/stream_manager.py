import logging
from typing import Any
from ..voice.tts_engine import AudioOutput

logger = logging.getLogger(__name__)


class StreamManager:
    """Manages audio streaming or playback for the broadcast."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_streams: dict[str, dict[str, Any]] = {}

    async def stream_audio(self, audio_output: AudioOutput) -> dict[str, Any]:
        """Stream audio for a segment and return a playback reference."""
        self.logger.info(
            f"Streaming audio for segment {audio_output.segment_id} "
            f"({audio_output.duration_seconds}s, {audio_output.language})"
        )

        stream_reference = {
            "segment_id": audio_output.segment_id,
            "audio_url": audio_output.audio_url or f"mock://{audio_output.segment_id}",
            "duration_seconds": audio_output.duration_seconds,
            "language": audio_output.language,
            "metadata": audio_output.metadata,
        }

        self.active_streams[audio_output.segment_id] = stream_reference
        return stream_reference

    async def stop_stream(self, segment_id: str) -> bool:
        """Stop an active audio stream."""
        if segment_id in self.active_streams:
            self.active_streams.pop(segment_id)
            self.logger.info(f"Stopped stream for segment {segment_id}")
            return True
        return False

    async def get_stream_status(self, segment_id: str) -> dict[str, Any]:
        """Get the stream status for a given segment."""
        return self.active_streams.get(segment_id, {})
