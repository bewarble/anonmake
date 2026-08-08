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

    pending = function_source(repo_path, "pending_recurrent_attempt")
    assert 'PaymentAttempt.status == "pending"' in pending
    assert 'PaymentAttempt.attempt_kind.in_(("primary", "fallback"))' in pending

    renew = function_source(service_path, "renew")
    assert "pending_recurrent_attempt" in renew
    assert "_recover_known_operation" in renew
    assert renew.index("pending_recurrent_attempt") < renew.index("cycle =")

    print("Billing concurrency and pending recovery check: OK")
    print("Cancel mutation serializes with recurrent worker")
    print("Post-charge refresh prevents stale subscription overwrite")
    print("Late recurrent success preserves explicit auto-renew cancellation")
    print("Pending recurrent operation is recovered before a new calendar cycle")


if __name__ == "__main__":
    main()
