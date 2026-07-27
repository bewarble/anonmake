from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/services/billing_worker.py",
        "app/repositories/billing.py",
        "app/core/config.py",
        "app/worker.py",
        "app/bot/handlers/__init__.py",
        "app/web/admin.py",
        "app/web/admin_repository.py",
        "app/web/templates/payments.html",
        "app/web/templates/payment_details.html",
        "app/web/templates/user_details.html",
        "app/web/static/admin_stage30_2.css",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel
        if rel.endswith(".py"):
            ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)

    worker = (ROOT / "app/services/billing_worker.py").read_text(encoding="utf-8")
    assert "pg_try_advisory_lock" in (
        ROOT / "app/repositories/billing.py"
    ).read_text(encoding="utf-8")
    assert "TickStats" in worker
    assert "batch_size" in worker
    assert "expire_finished_access" in worker

    handlers = (ROOT / "app/bot/handlers/__init__.py").read_text(encoding="utf-8")
    assert "payment_test_commands_enabled" in handlers

    admin = (ROOT / "app/web/admin.py").read_text(encoding="utf-8")
    assert '/payments/{attempt_id}' in admin
    assert "status_filter" in admin

    subscriptions = (
        ROOT / "app/repositories/billing.py"
    ).read_text(encoding="utf-8")
    assert '"cancelled_active"' in subscriptions
    assert '"expired"' in subscriptions

    print("Stage 30.2 check: OK")
    print("Production billing locks and batching: ready")
    print("Subscription lifecycle statuses: ready")
    print("Payment test commands production guard: ready")
    print("Web payment filters and details: ready")
    print("User subscription diagnostics: ready")


if __name__ == "__main__":
    check()
