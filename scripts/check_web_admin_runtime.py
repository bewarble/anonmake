from __future__ import annotations

import asyncio

from app.core.config import load_settings
from app.database.session import SessionFactory
from app.repositories.platform_admin import PlatformAdminRepository
from app.web.app import app

WEAK_BOOTSTRAP_PASSWORDS = {
    "admin",
    "changeme",
    "change-me",
    "password",
    "password123",
    "12345678",
    "123456789",
    "qwerty123",
}


async def check_bootstrap_admin() -> None:
    settings = load_settings()
    if not settings.web_admin_enabled:
        return

    async with SessionFactory() as session:
        admin_count = await PlatformAdminRepository(session).admin_count()

    if admin_count > 0:
        print(f"Web admin runtime: DB administrators configured: {admin_count}")
        return

    username = settings.web_admin_username.strip()
    password = settings.web_admin_password
    assert username, "WEB_ADMIN_USERNAME is required until the first DB administrator is created"
    assert len(password) >= 12, "Bootstrap WEB_ADMIN_PASSWORD must contain at least 12 characters"
    assert password.strip().lower() not in WEAK_BOOTSTRAP_PASSWORDS, "Bootstrap WEB_ADMIN_PASSWORD is a known weak/default password"
    assert password.strip().lower() != username.lower(), "Bootstrap WEB_ADMIN_PASSWORD must differ from WEB_ADMIN_USERNAME"
    print("Web admin runtime: bootstrap credential strength OK")


def check_routes() -> None:
    paths = {
        getattr(route, "path", "")
        for route in app.routes
    }

    required = {
        "/admin",
        "/admin/",
        "/admin/login",
        "/admin/users",
        "/admin/users/{user_id}",
        "/admin/payments",
        "/admin/sources",
        "/admin/delivery",
        "/admin/audit",
        "/health",
        "/metrics",
        "/payments/impaya/webhook",
    }
    missing = required - paths
    assert not missing, sorted(missing)

    print("Stage 26.1 runtime check: OK")
    print(f"Routes registered: {len(paths)}")
    print("Web admin and payment routes coexist")


async def main_async() -> None:
    check_routes()
    await check_bootstrap_admin()


def check() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    check()
