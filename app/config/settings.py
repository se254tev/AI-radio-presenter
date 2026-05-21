from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

base_dir = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(base_dir / ".env")


def _get_env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _get_env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _parse_redis_url(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"redis", "rediss"}:
        return {}
    path = parsed.path.lstrip("/")
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 6379,
        "db": int(path) if path.isdigit() else 0,
        "password": parsed.password,
    }


@dataclass
class RedisSettings:
    redis_url: Optional[str] = os.getenv("REDIS_URL")
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = _get_env_int("REDIS_PORT", 6379)
    db: int = _get_env_int("REDIS_DB", 0)
    password: Optional[str] = os.getenv("REDIS_PASSWORD")
    enable: bool = _get_env_bool("REDIS_ENABLE", True)

    def __post_init__(self):
        if self.redis_url:
            parsed = _parse_redis_url(self.redis_url)
            if parsed:
                self.host = parsed.get("host", self.host)
                self.port = parsed.get("port", self.port)
                self.db = parsed.get("db", self.db)
                self.password = parsed.get("password", self.password)


@dataclass
class DatabaseSettings:
    url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/radio_ai",
    )
    echo: bool = _get_env_bool("DB_ECHO", False)
    pool_size: int = _get_env_int("DB_POOL_SIZE", 20)
    max_overflow: int = _get_env_int("DB_MAX_OVERFLOW", 40)


@dataclass
class APISettings:
    openai_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    openai_temperature: float = _get_env_float("OPENAI_TEMPERATURE", 0.7)
    elevenlabs_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "default")


@dataclass
class BroadcastSettings:
    max_segment_duration: int = _get_env_int("MAX_SEGMENT_DURATION", 600)
    min_segment_duration: int = _get_env_int("MIN_SEGMENT_DURATION", 30)
    state_update_interval: float = _get_env_float("STATE_UPDATE_INTERVAL", 1.0)
    enable_audio: bool = _get_env_bool("ENABLE_AUDIO", True)
    enable_persistence: bool = _get_env_bool("ENABLE_PERSISTENCE", True)
    default_language: Literal["english", "swahili", "mixed"] = os.getenv("DEFAULT_LANGUAGE", "english")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


@dataclass
class AppSettings:
    environment: Literal["development", "staging", "production"] = os.getenv("APP_ENV", "development")
    debug: bool = _get_env_bool("DEBUG", False)
    app_name: str = os.getenv("APP_NAME", "AI Radio Presenter")
    version: str = os.getenv("APP_VERSION", "1.0.0")
    redis: RedisSettings = field(default_factory=RedisSettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    api: APISettings = field(default_factory=APISettings)
    broadcast: BroadcastSettings = field(default_factory=BroadcastSettings)


CONFIG = AppSettings()
