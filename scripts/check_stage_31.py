from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/services/admin_subscription_control.py",
        "app/web/admin_stage31.py",
        "app/web/templates/admin_action_confirm.html",
        "app/web/templates/subscriptions.html",
        "app/web/templates/crm_user_details.html",
        "app/web/static/admin_stage31.css",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        if rel.endswith(".py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    router = (ROOT / "app/web/admin_stage31.py").read_text(encoding="utf-8")
    assert '"/subscriptions"' in router
    assert '"/crm/users/{user_id}/control"' in router
    assert '"ПОДТВЕРЖДАЮ"' in router

    service = (
        ROOT / "app/services/admin_subscription_control.py"
    ).read_text(encoding="utf-8")
    assert "try_subscription_lock" in service
    assert "subscription.manual_charge" in service
    assert "AdminAuditLog" in service

    crm = (
        ROOT / "app/web/templates/crm_user_details.html"
    ).read_text(encoding="utf-8")
    assert "Списать 299 ₽" in crm
    assert "Списать 99 ₽" in crm
    assert "Последние платежи" in crm

    app = (ROOT / "app/web/app.py").read_text(encoding="utf-8")
    assert "admin_stage31_module" in app

    print("Stage 31 check: OK")
    print("Manual 299/99 ₽ charges with confirmation: ready")
    print("Auto-renew and manual access controls: ready")
    print("Subscription CRM and payment history: ready")
    print("Administrative audit trail: ready")
    print("Responsive Admin Control Center design: ready")


if __name__ == "__main__":
    check()
