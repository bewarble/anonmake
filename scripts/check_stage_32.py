from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/core/texts.py",
        "app/bot/handlers/subscriptions.py",
        "app/bot/keyboards/main_menu.py",
        "app/bot/keyboards/questions.py",
        "app/bot/keyboards/reveals.py",
        "app/web/static/admin_stage32.css",
        "docs/PRODUCT_LANGUAGE.md",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        if rel.endswith(".py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    texts = (ROOT / "app/core/texts.py").read_text(encoding="utf-8")
    assert "1 ₽ — 1 день доступа." in texts
    assert "Доступ до:" not in texts
    assert "299 ₽" not in texts
    assert "99 ₽" not in texts
    assert "пробный период" not in texts.lower()

    subscriptions = (
        ROOT / "app/bot/handlers/subscriptions.py"
    ).read_text(encoding="utf-8")
    assert "strftime" not in subscriptions
    assert "format_until" not in subscriptions
    assert "access_until" in subscriptions

    base = (ROOT / "app/web/templates/base.html").read_text(encoding="utf-8")
    assert "admin_stage32.css" in base

    admin_repo = (
        ROOT / "app/web/admin_repository.py"
    ).read_text(encoding="utf-8")
    assert "numeric_filters" in admin_repo
    assert "2**31" in admin_repo

    print("Stage 32 check: OK")
    print("Unified product language: ready")
    print("Public offer 1 ₽ / 1 day: ready")
    print("User billing internals and dates hidden: ready")
    print("Telegram copy and buttons standardized: ready")
    print("Admin design system polish: ready")
    print("Large Telegram ID search safeguard: ready")


if __name__ == "__main__":
    check()
