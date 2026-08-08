from __future__ import annotations

from sqlalchemy.engine import make_url

from app.core.config import load_settings
from app.core.platform_security import (
    platform_encryption_secret,
    validate_platform_encryption_secret,
)


WEAK_VALUES = {
    "admin",
    "anonmake",
    "change-me",
    "changeme",
    "password",
    "password123",
    "postgres",
    "qwerty123",
    "secret",
    "test",
}


def require_strong(name: str, value: str, *, minimum: int) -> None:
    normalized = value.strip()
    assert normalized, f"{name} must not be empty"
    assert len(normalized) >= minimum, f"{name} must contain at least {minimum} characters"
    assert normalized.casefold() not in WEAK_VALUES, f"{name} uses a known weak/default value"


def main() -> None:
    settings = load_settings()

    database = make_url(settings.database_url)
    database_password = database.password or ""
    require_strong("DATABASE_URL password", database_password, minimum=16)

    if settings.web_admin_enabled:
        require_strong("WEB_ADMIN_SECRET", settings.web_admin_secret, minimum=32)

    if settings.metrics_token.strip():
        require_strong("METRICS_TOKEN", settings.metrics_token, minimum=32)

    dedicated = platform_encryption_secret()
    if dedicated:
        validate_platform_encryption_secret(dedicated)
        assert dedicated != settings.web_admin_secret, (
            "PLATFORM_ENCRYPTION_SECRET must differ from WEB_ADMIN_SECRET"
        )

    print("Runtime secret strength check: OK")
    print("Database/admin/metrics/encryption credentials satisfy release minimums")


if __name__ == "__main__":
    main()
