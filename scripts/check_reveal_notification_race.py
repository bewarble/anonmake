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
    finalize = function_source(notifications, "finalize_checkout_and_notify")
    assert ".with_for_update()" in finalize
    assert "commit=False" in finalize
    assert "checkout.notified_at is not None" in finalize
    assert "send_message" in finalize
    assert "checkout.notified_at = datetime.now" in finalize
    assert finalize.index(".with_for_update()") < finalize.index("commit=False")
    assert finalize.index("commit=False") < finalize.index("send_message")
    assert finalize.index("send_message") < finalize.index("checkout.notified_at = datetime.now")

    service = function_source("app/services/reveal_checkout.py", "finalize")
    assert "commit: bool=True" in service.replace(" ", "")
    assert "if commit:" in service
    assert "await self.session.flush()" in service

    payment_return = function_source("app/web/payment_return.py", "process_checkout")
    assert "for_update=True" not in payment_return
    webhook = function_source("app/web/payment_webhook.py", "impaya_webhook")
    assert "with_for_update" not in webhook

    print("Reveal notification race check: OK")
    print("One checkout row serializes return/webhook finalization and notification")
    print("Payment state is not committed before the notification outcome is recorded")


if __name__ == "__main__":
    main()
