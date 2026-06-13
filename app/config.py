"""Application configuration loaded from environment / .env.

Secrets are read here and never logged. Settings are tolerant of two
naming schemes for the Telegram identifiers so the user's pre-existing
.env (ADMIN_ID / GROUP_ID) keeps working alongside the documented
TELEGRAM_ADMIN_ID / TELEGRAM_GROUP_ID names.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_env: str = Field(default="development")
    app_name: str = Field(default="PIAM CaseHub")
    base_url: str = Field(default="http://localhost:8000")
    secret_key: str = Field(default="change-me")
    tz: str = Field(default="America/Bahia")

    # --- Database ---
    database_url: str = Field(
        default="postgresql+psycopg://piam:piam@db:5432/piam"
    )

    # --- Telegram (accept both naming schemes) ---
    telegram_bot_token: str = Field(default="")
    telegram_admin_id: str = Field(default="", validation_alias="telegram_admin_id")
    telegram_group_id: str = Field(default="", validation_alias="telegram_group_id")
    # Fallback aliases matching the user's existing .env
    admin_id: str = Field(default="")
    group_id: str = Field(default="")

    # --- Admin web login ---
    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="change-me")

    # --- Uploads ---
    upload_dir: str = Field(default="/data/uploads")
    max_upload_mb: int = Field(default=25)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def resolved_admin_id(self) -> str:
        """Admin Telegram ID, preferring the documented name."""
        return self.telegram_admin_id or self.admin_id

    @property
    def resolved_group_id(self) -> str:
        """Group Telegram ID, preferring the documented name."""
        return self.telegram_group_id or self.group_id


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
