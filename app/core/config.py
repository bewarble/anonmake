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
    bot_username: str = Field(default="", alias="BOT_USERNAME")
    database_url: str = Field(
        default="sqlite+aiosqlite:///data/anonmake.db",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    json_logs: bool = Field(default=True, alias="JSON_LOGS")
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")

    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    broadcast_sender_telegram_id: int = Field(
        default=0, alias="BROADCAST_SENDER_TELEGRAM_ID"
    )

    web_admin_enabled: bool = Field(
        default=False,
        alias="WEB_ADMIN_ENABLED",
    )
    web_admin_username: str = Field(
        default="",
        alias="WEB_ADMIN_USERNAME",
    )
    web_admin_password: str = Field(
        default="",
        alias="WEB_ADMIN_PASSWORD",
    )
    web_admin_secret: str = Field(
        default="",
        alias="WEB_ADMIN_SECRET",
    )
    web_admin_session_minutes: int = Field(
        default=480,
        ge=5,
        le=10080,
        alias="WEB_ADMIN_SESSION_MINUTES",
    )
    web_admin_secure_cookie: bool = Field(
        default=True,
        alias="WEB_ADMIN_SECURE_COOKIE",
    )

    abuse_guard_enabled: bool = Field(default=True, alias="ABUSE_GUARD_ENABLED")
    question_burst_limit: int = Field(default=4, alias="QUESTION_BURST_LIMIT")
    question_burst_window_seconds: int = Field(
        default=8,
        alias="QUESTION_BURST_WINDOW_SECONDS",
    )
    question_minute_limit: int = Field(default=20, alias="QUESTION_MINUTE_LIMIT")
    question_duplicate_window_seconds: int = Field(
        default=180,
        alias="QUESTION_DUPLICATE_WINDOW_SECONDS",
    )

    billing_enabled: bool = Field(default=False, alias="BILLING_ENABLED")
    billing_worker_interval_seconds: int = Field(
        default=60,
        ge=5,
        alias="BILLING_WORKER_INTERVAL_SECONDS",
    )
    trial_price_kopecks: int = Field(default=100, ge=1, alias="TRIAL_PRICE_KOPECKS")
    trial_duration_hours: int = Field(default=24, ge=1, alias="TRIAL_DURATION_HOURS")
    primary_price_kopecks: int = Field(default=29900, ge=1, alias="PRIMARY_PRICE_KOPECKS")
    primary_duration_days: int = Field(default=3, ge=1, alias="PRIMARY_DURATION_DAYS")
    fallback_price_kopecks: int = Field(default=9900, ge=1, alias="FALLBACK_PRICE_KOPECKS")
    fallback_duration_days: int = Field(default=1, ge=1, alias="FALLBACK_DURATION_DAYS")
    trial_attempt_kinds: str = Field(default="trial", alias="TRIAL_ATTEMPT_KINDS")

    impaya_api_url: str = Field(
        default="https://ag-stage.impaya.ru",
        alias="IMPAYA_API_URL",
    )
    impaya_api_token: str = Field(default="", alias="IMPAYA_API_TOKEN")
    impaya_auth_header: str = Field(default="Authorization", alias="IMPAYA_AUTH_HEADER")
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
    impaya_webhook_secret: str = Field(default="", alias="IMPAYA_WEBHOOK_SECRET")
    offer_url: str = Field(default="", alias="OFFER_URL")
    public_base_url: str = Field(default="", alias="PUBLIC_BASE_URL")

    @property
    def admin_ids_set(self) -> set[int]:
        return {
            int(value)
            for raw in self.admin_ids.split(",")
            if (value := raw.strip()).isdigit()
        }

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
