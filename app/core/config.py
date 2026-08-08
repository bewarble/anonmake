from __future__ import annotations

from functools import lru_cache
import json

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
    bot_code: str = Field(default="primary", alias="BOT_CODE")
    bot_display_name: str = Field(default="AnonMake", alias="BOT_DISPLAY_NAME")
    multibot_tokens_json: str = Field(default="", alias="MULTIBOT_TOKENS_JSON")

    bot_two_code: str = Field(default="secondary", alias="BOT_TWO_CODE")
    bot_two_token: str = Field(default="", alias="BOT_TWO_TOKEN")
    bot_two_username: str = Field(default="", alias="BOT_TWO_USERNAME")
    bot_two_display_name: str = Field(default="Second Bot", alias="BOT_TWO_DISPLAY_NAME")
    bot_three_code: str = Field(default="third", alias="BOT_THREE_CODE")
    bot_three_token: str = Field(default="", alias="BOT_THREE_TOKEN")
    bot_three_username: str = Field(default="", alias="BOT_THREE_USERNAME")
    bot_three_display_name: str = Field(default="Third Bot", alias="BOT_THREE_DISPLAY_NAME")
    bot_four_code: str = Field(default="fourth", alias="BOT_FOUR_CODE")
    bot_four_token: str = Field(default="", alias="BOT_FOUR_TOKEN")
    bot_four_username: str = Field(default="", alias="BOT_FOUR_USERNAME")
    bot_four_display_name: str = Field(default="Fourth Bot", alias="BOT_FOUR_DISPLAY_NAME")

    database_url: str = Field(default="sqlite+aiosqlite:///data/anonmake.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    json_logs: bool = Field(default=True, alias="JSON_LOGS")
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")

    performance_enabled: bool = Field(default=True, alias="PERFORMANCE_ENABLED")
    performance_profile_enabled: bool = Field(default=False, alias="PERF_PROFILE_ENABLED")
    performance_slow_operation_ms: int = Field(default=500, ge=10, alias="PERF_SLOW_OPERATION_MS")
    performance_slow_sql_ms: int = Field(default=150, ge=10, alias="PERF_SLOW_SQL_MS")
    worker_idle_max_seconds: float = Field(default=10.0, ge=1.0, le=60.0, alias="WORKER_IDLE_MAX_SECONDS")
    metrics_token: str = Field(default="", alias="METRICS_TOKEN")

    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    broadcast_sender_telegram_id: int = Field(default=0, alias="BROADCAST_SENDER_TELEGRAM_ID")

    web_admin_enabled: bool = Field(default=False, alias="WEB_ADMIN_ENABLED")
    web_admin_username: str = Field(default="", alias="WEB_ADMIN_USERNAME")
    web_admin_password: str = Field(default="", alias="WEB_ADMIN_PASSWORD")
    web_admin_secret: str = Field(default="", alias="WEB_ADMIN_SECRET")
    web_admin_session_minutes: int = Field(default=480, ge=5, le=10080, alias="WEB_ADMIN_SESSION_MINUTES")
    web_admin_secure_cookie: bool = Field(default=True, alias="WEB_ADMIN_SECURE_COOKIE")

    abuse_guard_enabled: bool = Field(default=True, alias="ABUSE_GUARD_ENABLED")
    question_burst_limit: int = Field(default=4, alias="QUESTION_BURST_LIMIT")
    question_burst_window_seconds: int = Field(default=8, alias="QUESTION_BURST_WINDOW_SECONDS")
    question_minute_limit: int = Field(default=20, alias="QUESTION_MINUTE_LIMIT")
    question_duplicate_window_seconds: int = Field(default=180, alias="QUESTION_DUPLICATE_WINDOW_SECONDS")

    billing_enabled: bool = Field(default=False, alias="BILLING_ENABLED")
    billing_worker_interval_seconds: int = Field(default=60, ge=5, alias="BILLING_WORKER_INTERVAL_SECONDS")
    billing_automatic_charges_enabled: bool = Field(default=False, alias="BILLING_AUTOMATIC_CHARGES_ENABLED")
    billing_worker_batch_size: int = Field(default=100, ge=1, le=1000, alias="BILLING_WORKER_BATCH_SIZE")
    payment_test_commands_enabled: bool = Field(default=False, alias="PAYMENT_TEST_COMMANDS_ENABLED")
    trial_price_kopecks: int = Field(default=100, ge=1, alias="TRIAL_PRICE_KOPECKS")
    trial_duration_hours: int = Field(default=24, ge=1, alias="TRIAL_DURATION_HOURS")
    primary_price_kopecks: int = Field(default=29900, ge=1, alias="PRIMARY_PRICE_KOPECKS")
    primary_duration_days: int = Field(default=3, ge=1, alias="PRIMARY_DURATION_DAYS")
    fallback_price_kopecks: int = Field(default=9900, ge=1, alias="FALLBACK_PRICE_KOPECKS")
    fallback_duration_days: int = Field(default=1, ge=1, alias="FALLBACK_DURATION_DAYS")
    trial_attempt_kinds: str = Field(default="trial", alias="TRIAL_ATTEMPT_KINDS")

    impaya_api_url: str = Field(default="https://ag-stage.impaya.ru", alias="IMPAYA_API_URL")
    impaya_api_token: str = Field(default="", alias="IMPAYA_API_TOKEN")
    impaya_auth_header: str = Field(default="Authorization", alias="IMPAYA_AUTH_HEADER")
    impaya_auth_prefix: str = Field(default="Bearer ", alias="IMPAYA_AUTH_PREFIX")
    impaya_protocol_version: str = Field(default="v2.0", alias="IMPAYA_PROTOCOL_VERSION")
    impaya_terminal_name: str = Field(default="evocloud.su_3ds_test", alias="IMPAYA_TERMINAL_NAME")
    impaya_binding_terminal_name: str = Field(default="", alias="IMPAYA_BINDING_TERMINAL_NAME")
    impaya_recurrent_terminal_name: str = Field(default="", alias="IMPAYA_RECURRENT_TERMINAL_NAME")
    impaya_payment_form_url_template: str = Field(default="", alias="IMPAYA_PAYMENT_FORM_URL_TEMPLATE")
    impaya_webhook_secret: str = Field(default="", alias="IMPAYA_WEBHOOK_SECRET")
    offer_url: str = Field(default="", alias="OFFER_URL")
    public_base_url: str = Field(default="", alias="PUBLIC_BASE_URL")

    @property
    def admin_ids_set(self) -> set[int]:
        return {int(value) for raw in self.admin_ids.split(",") if (value := raw.strip()).isdigit()}

    def bot_tokens(self) -> dict[str, str]:
        tokens: dict[str, str] = {}
        configured = (
            (self.bot_code, self.bot_token),
            (self.bot_two_code, self.bot_two_token),
            (self.bot_three_code, self.bot_three_token),
            (self.bot_four_code, self.bot_four_token),
        )
        for raw_code, raw_token in configured:
            code = raw_code.strip().lower()
            token = raw_token.strip()
            if code and token:
                tokens[code] = token

        raw = self.multibot_tokens_json.strip()
        if raw:
            try:
                loaded = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RuntimeError("MULTIBOT_TOKENS_JSON is invalid JSON") from exc
            if not isinstance(loaded, dict):
                raise RuntimeError("MULTIBOT_TOKENS_JSON must be an object")
            for code, token in loaded.items():
                normalized_code = str(code).strip().lower()
                normalized_token = str(token).strip()
                if not normalized_code or not normalized_token:
                    raise RuntimeError("MULTIBOT_TOKENS_JSON contains an empty key or token")
                tokens[normalized_code] = normalized_token
        return tokens

    def configured_bot_identities(self) -> tuple[tuple[str, str, str, str], ...]:
        items = (
            (self.bot_code, self.bot_token, self.bot_username, self.bot_display_name),
            (self.bot_two_code, self.bot_two_token, self.bot_two_username, self.bot_two_display_name),
            (self.bot_three_code, self.bot_three_token, self.bot_three_username, self.bot_three_display_name),
            (self.bot_four_code, self.bot_four_token, self.bot_four_username, self.bot_four_display_name),
        )
        configured: list[tuple[str, str, str, str]] = []
        seen_codes: set[str] = set()
        seen_usernames: set[str] = set()
        for raw_code, raw_token, raw_username, raw_name in items:
            token = raw_token.strip()
            if not token:
                continue
            code = raw_code.strip().lower()
            username = raw_username.strip().lstrip("@")
            display_name = raw_name.strip() or username
            if not code:
                raise RuntimeError("Configured bot has an empty code")
            if not username:
                raise RuntimeError(f"BOT username is missing for configured code: {code}")
            if code in seen_codes:
                raise RuntimeError(f"Duplicate bot code: {code}")
            if username.lower() in seen_usernames:
                raise RuntimeError(f"Duplicate bot username: {username}")
            seen_codes.add(code)
            seen_usernames.add(username.lower())
            configured.append((code, token, username, display_name))
        return tuple(configured)

    def require_bot_identity(self) -> tuple[str, str, str]:
        code = self.bot_code.strip().lower()
        username = self.bot_username.strip().lstrip("@")
        display_name = self.bot_display_name.strip()
        if not code:
            raise RuntimeError("BOT_CODE is missing")
        if not username:
            raise RuntimeError("BOT_USERNAME is missing")
        if not display_name:
            display_name = username
        return code, username, display_name

    def require_bot_token(self) -> str:
        token = self.bot_token.strip()
        if not token:
            raise RuntimeError("BOT_TOKEN is missing. Create .env from .env.example and add the token.")
        return token


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    return Settings()
