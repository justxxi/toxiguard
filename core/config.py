from __future__ import annotations

from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = ""
    db_url: str = "sqlite+aiosqlite:///toxiguard.db"
    log_level: str = "INFO"

    default_threshold: float = 0.75
    mute_after: int = 3
    mute_duration: timedelta = timedelta(hours=1)
    max_mute_duration: timedelta = timedelta(days=366)

    min_text_len: int = 3
    cache_size: int = 4096
    model_name: str = "multilingual"
    ml_concurrency: int = 4

    admin_cache_ttl: float = 60.0
    event_retention_days: int = 90
    dashboard_password: str = ""
    redis_url: str = "redis://localhost:6379"


settings = Settings()
