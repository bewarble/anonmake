from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import HTTPException, Request, status

from app.core.config import Settings


COOKIE_NAME = "anonmake_admin_session"


@dataclass(slots=True, frozen=True)
class AdminSession:
    username: str
    expires_at: datetime


class AdminAuth:
    """Small signed-cookie authentication layer for the internal admin UI."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def ensure_configured(self) -> None:
        if not self.settings.web_admin_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Web admin is disabled",
            )

        if not self.settings.web_admin_username.strip():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WEB_ADMIN_USERNAME is not configured",
            )

        if not self.settings.web_admin_password:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WEB_ADMIN_PASSWORD is not configured",
            )

        if len(self.settings.web_admin_secret.strip()) < 32:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WEB_ADMIN_SECRET must contain at least 32 characters",
            )

    def verify_credentials(self, username: str, password: str) -> bool:
        self.ensure_configured()
        return (
            hmac.compare_digest(
                username.strip(),
                self.settings.web_admin_username.strip(),
            )
            and hmac.compare_digest(
                password,
                self.settings.web_admin_password,
            )
        )

    def create_token(self) -> str:
        self.ensure_configured()
        username = self.settings.web_admin_username.strip()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self.settings.web_admin_session_minutes
        )
        nonce = secrets.token_urlsafe(18)
        payload = f"{username}|{int(expires_at.timestamp())}|{nonce}"
        return f"{payload}|{self._sign(payload)}"

    def parse_token(self, token: str | None) -> AdminSession | None:
        if not token:
            return None

        try:
            username, expires_raw, nonce, signature = token.split("|", 3)
            payload = f"{username}|{expires_raw}|{nonce}"
            if not hmac.compare_digest(signature, self._sign(payload)):
                return None
            expires_at = datetime.fromtimestamp(
                int(expires_raw),
                tz=timezone.utc,
            )
        except (TypeError, ValueError, OverflowError):
            return None

        if expires_at <= datetime.now(timezone.utc):
            return None

        if not hmac.compare_digest(
            username,
            self.settings.web_admin_username.strip(),
        ):
            return None

        return AdminSession(username=username, expires_at=expires_at)

    def session_from_request(self, request: Request) -> AdminSession | None:
        return self.parse_token(request.cookies.get(COOKIE_NAME))

    def _sign(self, payload: str) -> str:
        return hmac.new(
            self.settings.web_admin_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
