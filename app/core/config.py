from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: str = Field(default="", alias="BOT_TOKEN")
    database_url: str = Field(
        default="sqlite+aiosqlite:///data/anonmake.db",
        alias="DATABASE_URL",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")

    def require_bot_token(self) -> str:
        token = self.bot_token.strip()
        if not token:
            raise RuntimeError(
                "BOT_TOKEN is missing. Create .env from .env.example and add the token."
            )
        return token


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    return Settings()
