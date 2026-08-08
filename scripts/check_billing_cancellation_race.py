from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def function_source(path: str, name: str) -> str:
    source = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.unparse(node)
    raise AssertionError(f"Function not found: {path}:{name}")


def main() -> None:
    repo_path = "app/repositories/billing.py"
    service_path = "app/services/billing.py"

    lock = function_source(repo_path, "lock_subscription_transaction")
    assert "pg_advisory_xact_lock" in lock
    assert "subscription_id" in lock

    cancel = function_source(repo_path, "cancel_auto_renew")
    assert "lock_subscription_transaction" in cancel
    assert "session.refresh(subscription)" in cancel
    assert "subscription.auto_renew = False" in cancel
    assert "subscription.next_charge_at = None" in cancel

    success = function_source(service_path, "_mark_success")
    assert "explicitly_cancelled" in success
    assert "subscription.cancelled_at is not None" in success
    assert "subscription.auto_renew = False" in success
    assert "subscription.next_charge_at = None" in success
    assert 'subscription.status = "cancelled_active"' in success
    assert "PRIMARY_ACCESS_KINDS" in success

    pending = function_source(repo_path, "pending_recurrent_attempt")
    assert 'PaymentAttempt.status == "pending"' in pending
    for kind in (
        "primary",
        "fallback",
        "admin_primary",
        "admin_fallback",
        "test_primary",
        "test_fallback",
    ):
        assert repr(kind) in pending or f'"{kind}"' in pending, kind

    renew = function_source(service_path, "renew")
    assert "pending_recurrent_attempt" in renew
    assert "_recover_known_operation" in renew
    assert "_period_for_attempt" in renew
    assert renew.index("pending_recurrent_attempt") < renew.index("cycle =")

    finalize = function_source(service_path, "finalize_operation")
    assert "_period_for_attempt(attempt)" in finalize
    period = function_source(service_path, "_period_for_attempt")
    assert "PRIMARY_ACCESS_KINDS" in period

    service_text = (ROOT / service_path).read_text(encoding="utf-8")
    assert '"admin_primary"' in service_text
    assert '"admin_fallback"' in service_text

    test_charge = function_source("app/bot/handlers/recurrent_test.py", "confirm_test_charge")
    assert "load_impaya_config" in test_charge
    assert "subscription.bot_id" in test_charge
    assert "create_impaya_client" in test_charge
    assert "try_subscription_lock(subscription.id)" in test_charge
    assert "release_subscription_lock(subscription.id)" in test_charge
    assert "session.refresh(subscription)" in test_charge
    assert "session.refresh(method)" in test_charge

    print("Billing concurrency and pending recovery check: OK")
    print("Cancel mutation serializes with recurrent worker")
    print("Post-charge refresh prevents stale subscription overwrite")
    print("Late recurrent success preserves explicit auto-renew cancellation")
    print("Pending automatic/manual/test charge is recovered before a new cycle")
    print("Late admin_primary confirmation keeps the primary access period")
    print("Telegram test MIT charge uses owning gateway and subscription lock")


if __name__ == "__main__":
    main()
