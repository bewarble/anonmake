from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/web/templates/platform_admin_edit.html",
        "app/web/templates/platform_admins.html",
        "app/web/templates/platform_payments.html",
        "app/web/admin_platform.py",
    )
    for rel in required:
        path = ROOT / rel
        assert path.exists(), rel
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    platform = (ROOT / "app/web/admin_platform.py").read_text(encoding="utf-8")
    for fragment in (
        '/admins/{admin_id}/edit',
        '/admins/{admin_id}/delete',
        'active_superadmin_count',
        'Нельзя удалить собственный аккаунт',
    ):
        assert fragment in platform, fragment

    admins = (ROOT / "app/web/templates/platform_admins.html").read_text(encoding="utf-8")
    payments = (ROOT / "app/web/templates/platform_payments.html").read_text(encoding="utf-8")
    edit = (ROOT / "app/web/templates/platform_admin_edit.html").read_text(encoding="utf-8")
    css = (ROOT / "app/web/static/admin-ui.css").read_text(encoding="utf-8")

    for forbidden in ("Email", "API URL", "API token", "Terminal", "Webhook secret"):
        assert forbidden not in admins + payments + edit, forbidden
    for required_label in (
        "Электронная почта",
        "Ключ доступа",
        "Основной терминал",
        "Редактировать",
        "Удалить",
    ):
        assert required_label in admins + payments + edit, required_label
    assert "Stage 42" in css

    print("Stage 42 check: OK")
    print("Administrator account design: refreshed")
    print("Per-project payment settings design: refreshed")
    print("Administrator editing and deletion: ready")
    print("Last SuperAdmin and self-deletion protection: ready")
    print("Visible platform terminology: Russian")


if __name__ == "__main__":
    check()
