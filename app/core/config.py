from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    question_burst_limit: int = Field(default=4, alias="QUESTION_BURST_LIMIT")
    question_burst_window_seconds: int = Field(default=8, alias="QUESTION_BURST_WINDOW_SECONDS")
    question_minute_limit: int = Field(default=20, alias="QUESTION_MINUTE_LIMIT")
    question_duplicate_window_seconds: int = Field(default=180, alias="QUESTION_DUPLICATE_WINDOW_SECONDS")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")

    @property
    def admin_ids_set(self) -> set[int]:
        result: set[int] = set()
        for value in self.admin_ids.split(','):
            value = value.strip()
            if value.isdigit():
                result.add(int(value))
        return result
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    json_logs: bool = Field(default=True, alias="JSON_LOGS")
    abuse_guard_enabled: bool = Field(default=True, alias="ABUSE_GUARD_ENABLED")
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

    billing_enabled: bool = Field(default=False, alias="BILLING_ENABLED")
    impaya_api_url: str = Field(
        default="https://ag-stage.impaya.ru",
        alias="IMPAYA_API_URL",
    )
    impaya_api_token: str = Field(default="", alias="IMPAYA_API_TOKEN")
    impaya_auth_header: str = Field(
        default="Authorization",
        alias="IMPAYA_AUTH_HEADER",
    )
    impaya_auth_prefix: str = Field(default="Bearer ", alias="IMPAYA_AUTH_PREFIX")
    impaya_protocol_version: str = Field(default="v2.0", alias="IMPAYA_PROTOCOL_VERSION")
    impaya_terminal_name: str = Field(
        default="evocloud.su_3ds_test",
        alias="IMPAYA_TERMINAL_NAME",
    )
    impaya_payment_form_url_template: str = Field(
        default="",
        alias="IMPAYA_PAYMENT_FORM_URL_TEMPLATE",
    )
    offer_url: str = Field(default="", alias="OFFER_URL")
    public_base_url: str = Field(default="", alias="PUBLIC_BASE_URL")
    impaya_webhook_secret: str = Field(default="", alias="IMPAYA_WEBHOOK_SECRET")
    billing_worker_interval_seconds: int = Field(default=60, alias="BILLING_WORKER_INTERVAL_SECONDS")

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
