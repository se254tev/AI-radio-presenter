from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ValidationInfo

from pathlib import Path


class RedisConfig(BaseSettings):
    redis_url: str = Field("", env="REDIS_URL")
    enable: bool = Field(True, env="REDIS_ENABLE")

    model_config = {"env_prefix": ""}

    @field_validator("redis_url", mode="after")
    @classmethod
    def validate_redis_url(cls, v: str, info: ValidationInfo) -> str:
        """Ensure REDIS_URL is provided when REDIS_ENABLE is True."""
        enable = info.data.get("enable", True)
        if enable and not v:
            raise ValueError("REDIS_URL must be provided when REDIS_ENABLE=true")
        return v


class DatabaseConfig(BaseSettings):
    database_url: str | None = Field(None, env="DATABASE_URL")
    supabase_url: str | None = Field(None, env="SUPABASE_URL")
    supabase_key: str | None = Field(None, env="SUPABASE_KEY")

    model_config = {"env_prefix": ""}


class MongoConfig(BaseSettings):
    mongo_uri: str = Field("mongodb://localhost:27017", env="MONGO_URI")
    mongo_db: str = Field("radio_ai", env="MONGO_DB_NAME")

    model_config = {"env_prefix": ""}


class APIConfig(BaseSettings):
    openai_api_key: str | None = Field(None, env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4-turbo", env="OPENAI_MODEL")
    openai_temperature: float = Field(0.7, env="OPENAI_TEMPERATURE")
    elevenlabs_api_key: str | None = Field(None, env="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field("default", env="ELEVENLABS_VOICE_ID")

    model_config = {"env_prefix": ""}


class BroadcastConfig(BaseSettings):
    max_segment_duration: int = Field(600, env="MAX_SEGMENT_DURATION")
    min_segment_duration: int = Field(30, env="MIN_SEGMENT_DURATION")
    state_update_interval: float = Field(1.0, env="STATE_UPDATE_INTERVAL")
    enable_audio: bool = Field(True, env="ENABLE_AUDIO")
    enable_persistence: bool = Field(True, env="ENABLE_PERSISTENCE")
    default_language: str = Field("english", env="DEFAULT_LANGUAGE")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    model_config = {"env_prefix": ""}


class Settings(BaseSettings):
    # App
    app_name: str = Field("AI Radio Presenter", env="APP_NAME")
    environment: str = Field("development", env="APP_ENV")
    debug: bool = Field(False, env="DEBUG")
    version: str = Field("1.0.0", env="VERSION")

    # Databases
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    mongo: MongoConfig = Field(default_factory=MongoConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)

    # APIs
    api: APIConfig = Field(default_factory=APIConfig)

    # Broadcast
    broadcast: BroadcastConfig = Field(default_factory=BroadcastConfig)

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


CONFIG = Settings()
