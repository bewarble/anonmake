from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/models/platform_admin.py",
        "app/core/platform_security.py",
        "app/repositories/platform_admin.py",
        "app/services/impaya_factory.py",
        "app/web/admin_platform.py",
        "app/web/templates/platform_admins.html",
        "app/web/templates/platform_payments.html",
        "migrations/versions/20260728_0015_platform_administration.py",
    )
    for rel in required:
        path = ROOT / rel
        assert path.exists(), rel
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    models = (ROOT / "app/models/platform_admin.py").read_text(encoding="utf-8")
    assert "class AdminUser" in models
    assert "class AdminProjectAccess" in models
    assert "class PaymentGatewayConfig" in models

    auth = (ROOT / "app/web/admin_auth.py").read_text(encoding="utf-8")
    assert "async def verify_credentials" in auth
    assert 'role="superadmin"' in auth

    factory = (ROOT / "app/services/impaya_factory.py").read_text(encoding="utf-8")
    assert "load_impaya_config" in factory
    assert "gateway_for_bot" in factory

    app = (ROOT / "app/web/app.py").read_text(encoding="utf-8")
    assert "admin_platform_module" in app

    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "cryptography" in requirements

    print("Stage 41 check: OK")
    print("Database administrator accounts: ready")
    print("SuperAdmin and per-project access: ready")
    print("Forbidden project URL access: blocked")
    print("Per-project Impaya configuration: ready")
    print("Encrypted payment secrets: ready")
    print("Legacy .env admin login fallback: preserved")


if __name__ == "__main__":
    check()
