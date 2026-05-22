"""
AI DJ Service - LLM-based radio host with context memory
"""
import logging
from typing import Any
import asyncio

logger = logging.getLogger(__name__)


class AIRadioHost:
    """AI-powered radio DJ using LLM for dynamic commentary and transitions"""

    def __init__(
        self,
        openai_api_key: str = "",
        model: str = "gpt-4-turbo",
        temperature: float = 0.7,
    ):
        self.api_key = openai_api_key
        self.model = model
        self.temperature = temperature
        self.context = {
            "show_name": "AI Radio",
            "current_track": None,
            "previous_tracks": [],
            "listener_count": 0,
            "show_theme": "general",
        }
        self._client = None

    async def initialize(self) -> None:
        """Initialize OpenAI client"""
        if not self.api_key:
            logger.warning("OpenAI API key not set; AI features will be limited")
            return
        
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
            logger.info("AI DJ initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI client: {e}")

    async def generate_show_intro(self, show_name: str) -> str:
        """Generate opening statement for the show"""
        if not self._client:
            return f"Welcome to {show_name}!"

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an enthusiastic radio DJ. Generate a short, energetic show intro (1-2 sentences max).",
                    },
                    {
                        "role": "user",
                        "content": f"Create an intro for a radio show called '{show_name}'",
                    },
                ],
                max_tokens=100,
            )
            text = response.choices[0].message.content.strip()
            logger.info(f"Generated show intro: {text[:50]}...")
            return text
        except Exception as e:
            logger.error(f"Failed to generate intro: {e}")
            return f"Welcome to {show_name}!"

    async def generate_transition(
        self, current_track: str, next_track: str
    ) -> str:
        """Generate commentary between tracks"""
        if not self._client:
            return f"Now playing {next_track}..."

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a smooth radio DJ. Generate a brief transition between songs (1-2 sentences).",
                    },
                    {
                        "role": "user",
                        "content": f"Previous track: '{current_track}'. Next track: '{next_track}'. Create a smooth transition.",
                    },
                ],
                max_tokens=100,
            )
            text = response.choices[0].message.content.strip()
            logger.info(f"Generated transition: {text[:50]}...")
            return text
        except Exception as e:
            logger.error(f"Failed to generate transition: {e}")
            return f"Now playing {next_track}..."

    async def respond_to_message(self, user_message: str) -> str:
        """Generate AI DJ response to listener interaction"""
        if not self._client:
            return "Thanks for tuning in!"

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a friendly radio DJ responding to listener messages. Keep responses brief (1-2 sentences).",
                    },
                    {"role": "user", "content": user_message},
                ],
                max_tokens=100,
            )
            text = response.choices[0].message.content.strip()
            return text
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return "Thanks for the message!"

    def update_context(self, updates: dict[str, Any]) -> None:
        """Update internal context for better commentary"""
        self.context.update(updates)
        logger.debug(f"Context updated: {updates}")

    async def get_show_status(self) -> dict[str, Any]:
        """Return current show metadata"""
        return {
            "status": "live" if self._client else "limited_mode",
            "context": self.context,
            "model": self.model if self._client else "fallback",
        }
