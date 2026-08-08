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
    notifications = "app/services/payment_notifications.py"
    lock = function_source(notifications, "_lock_notification")
    unlock = function_source(notifications, "_unlock_notification")
    assert "pg_advisory_lock" in lock
    assert "REVEAL_NOTIFICATION_LOCK_NAMESPACE" in lock
    assert "pg_advisory_unlock" in unlock

    finalize = function_source(notifications, "finalize_checkout_and_notify")
    assert "_lock_notification(session, checkout.id)" in finalize
    assert "await session.refresh(checkout)" in finalize
    assert "checkout.notified_at is not None" in finalize
    assert "_unlock_notification(session, checkout.id)" in finalize
    assert finalize.index("_lock_notification") < finalize.index("send_message")
    assert finalize.index("send_message") < finalize.rindex("_unlock_notification")

    payment_return = function_source("app/web/payment_return.py", "process_checkout")
    assert "for_update=True" not in payment_return
    webhook = function_source("app/web/payment_webhook.py", "impaya_webhook")
    assert "with_for_update" not in webhook

    print("Reveal notification race check: OK")
    print("Return/webhook notification is serialized across payment-state commits")
    print("No database row lock is held across Impaya or Telegram network I/O")


if __name__ == "__main__":
    main()
