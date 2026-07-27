from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/web/admin.py",
        "app/web/admin_auth.py",
        "app/web/admin_repository.py",
        "app/web/app.py",
        "app/web/static/admin.css",
        "app/web/templates/base.html",
        "app/web/templates/login.html",
        "app/web/templates/dashboard.html",
        "app/web/templates/users.html",
        "app/web/templates/user_details.html",
        "app/web/templates/payments.html",
        "app/web/templates/sources.html",
        "app/web/templates/delivery.html",
        "app/web/templates/audit.html",
        "app/web/templates/pagination.html",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel

    for rel in (
        "app/web/admin.py",
        "app/web/admin_auth.py",
        "app/web/admin_repository.py",
        "app/web/app.py",
        "app/core/config.py",
    ):
        ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)

    app_text = (ROOT / "app/web/app.py").read_text(encoding="utf-8")
    assert "app.include_router(admin_router)" in app_text
    assert '"/admin/static"' in app_text

    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for name in ("prometheus-client", "jinja2", "python-multipart"):
        assert name in requirements, name

    config = (ROOT / "app/core/config.py").read_text(encoding="utf-8")
    for field in (
        "web_admin_enabled",
        "web_admin_username",
        "web_admin_password",
        "web_admin_secret",
        "web_admin_session_minutes",
        "web_admin_secure_cookie",
    ):
        assert field in config, field

    print("Stage 26.1 structural check: OK")
    print("Router registration: verified")
    print("Templates and static assets: verified")
    print("Requirements: complete")
    print("Configuration: complete")


if __name__ == "__main__":
    check()
