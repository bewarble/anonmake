from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import HTTPException, Request, status

from app.core.config import Settings
from app.core.platform_security import verify_password
from app.database.session import SessionFactory
from app.repositories.platform_admin import PlatformAdminRepository


COOKIE_NAME = "anonmake_admin_session"
DUMMY_PASSWORD_HASH = (
    "pbkdf2_sha256$310000$YW5vbm1ha2UtYWRtaW4tZHVtbXk=$"
    "zkPEwbUk5cc-1vtbQhwIMQYWCz34za55hLx-A7_Oz_U="
)


@dataclass(slots=True, frozen=True)
class AdminSession:
    admin_id: int | None
    username: str
    role: str
    issued_at: datetime
    expires_at: datetime

    @property
    def is_superadmin(self) -> bool:
        return self.role == "superadmin"


class AdminAuth:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def ensure_configured(self) -> None:
        if not self.settings.web_admin_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Web admin is disabled",
            )
        if len(self.settings.web_admin_secret.strip()) < 32:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WEB_ADMIN_SECRET must contain at least 32 characters",
            )

    async def verify_credentials(
        self, username: str, password: str
    ) -> AdminSession | None:
        self.ensure_configured()
        normalized = username.strip().lower()
        now = datetime.now(timezone.utc)

        async with SessionFactory() as session:
            repo = PlatformAdminRepository(session)
            admin = await repo.admin_by_email(normalized)
            if admin is not None:
                password_ok = verify_password(password, admin.password_hash)
                if password_ok:
                    await repo.mark_login(admin)
                    return AdminSession(
                        admin_id=admin.id,
                        username=admin.email,
                        role=admin.role,
                        issued_at=now,
                        expires_at=now,
                    )
            else:
                verify_password(password, DUMMY_PASSWORD_HASH)
            admin_count = await repo.admin_count()

        if (
            admin_count == 0
            and self.settings.web_admin_username.strip()
            and self.settings.web_admin_password
            and hmac.compare_digest(
                normalized,
                self.settings.web_admin_username.strip().lower(),
            )
            and hmac.compare_digest(password, self.settings.web_admin_password)
        ):
            return AdminSession(
                admin_id=None,
                username=self.settings.web_admin_username.strip(),
                role="superadmin",
                issued_at=now,
                expires_at=now,
            )
        return None

    def create_token(self, principal: AdminSession) -> str:
        self.ensure_configured()
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(
            minutes=self.settings.web_admin_session_minutes
        )
        nonce = secrets.token_urlsafe(18)
        admin_id = principal.admin_id or 0
        payload = (
            f"{admin_id}|{principal.username}|{principal.role}|"
            f"{int(issued_at.timestamp())}|{int(expires_at.timestamp())}|{nonce}"
        )
        return f"{payload}|{self._sign(payload)}"

    def parse_token(self, token: str | None) -> AdminSession | None:
        if not token:
            return None
        try:
            (
                admin_raw,
                username,
                role,
                issued_raw,
                expires_raw,
                nonce,
                signature,
            ) = token.split("|", 6)
            payload = (
                f"{admin_raw}|{username}|{role}|{issued_raw}|"
                f"{expires_raw}|{nonce}"
            )
            if not hmac.compare_digest(signature, self._sign(payload)):
                return None
            issued_at = datetime.fromtimestamp(int(issued_raw), tz=timezone.utc)
            expires_at = datetime.fromtimestamp(int(expires_raw), tz=timezone.utc)
            admin_id = int(admin_raw) or None
        except (TypeError, ValueError, OverflowError):
            return None
        now = datetime.now(timezone.utc)
        if issued_at > now + timedelta(minutes=1) or expires_at <= now:
            return None
        return AdminSession(
            admin_id=admin_id,
            username=username,
            role=role,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    def session_from_request(self, request: Request) -> AdminSession | None:
        return self.parse_token(request.cookies.get(COOKIE_NAME))

    def _sign(self, payload: str) -> str:
        return hmac.new(
            self.settings.web_admin_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
