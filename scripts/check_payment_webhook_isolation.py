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
    webhook = "app/web/payment_webhook.py"
    handler = function_source(webhook, "impaya_webhook")
    assert "_owner_for_operation" in handler
    assert "load_impaya_config(session, settings, bot_id)" in handler
    assert "_verify_project_secret(x_webhook_secret, config.webhook_secret)" in handler
    assert handler.index("_owner_for_operation") < handler.index("_verify_project_secret")

    owner = function_source(webhook, "_owner_for_operation")
    assert "RevealCheckout.customer_operation_id == operation_id" in owner
    assert "PaymentAttempt.customer_operation_id == operation_id" in owner
    assert "select(User.bot_id)" in owner
    assert "select(PaymentAttempt.bot_id)" in owner

    verifier = function_source(webhook, "_verify_project_secret")
    assert "hmac.compare_digest" in verifier
    assert "Webhook secret is not configured" in verifier

    installer = function_source(webhook, "install_impaya_webhook")
    assert "app.router.routes[:]" in installer
    assert "WEBHOOK_PATH" in installer
    assert "app.add_api_route" in installer
    assert "project_impaya_webhook_installed" in installer

    system = (ROOT / "app/web/admin_system.py").read_text(encoding="utf-8")
    assert "from app.web.payment_webhook import install_impaya_webhook" in system
    assert "install_impaya_webhook(web_app)" in system

    print("Payment webhook project isolation check: OK")
    print("Operation owner is resolved before webhook authentication")
    print("Owning project Impaya secret authenticates the callback")
    print("Legacy global-secret route is replaced, not duplicated")


if __name__ == "__main__":
    main()
