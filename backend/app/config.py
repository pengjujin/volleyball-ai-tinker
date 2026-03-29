from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Volleyball AI"
    app_version: str = "0.1.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    default_ruleset_variant: str = Field(default="6-player")
    storage_root: str = Field(default="/tmp/volleyball_ai")
    gemini_live_enabled: bool = Field(default=False)
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "VOLLEYBALL_AI_GEMINI_API_KEY",
            "GEMINI_API_KEY",
        ),
    )
    gemini_model: str = Field(default="gemini-2.5-pro")
    gemini_video_fps: float = Field(default=2.0, gt=0.0)
    gemini_inline_video_max_bytes: int = Field(default=20 * 1024 * 1024, gt=0)

    model_config = SettingsConfigDict(
        env_prefix="VOLLEYBALL_AI_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
