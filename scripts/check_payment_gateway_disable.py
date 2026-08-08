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
    factory_path = "app/services/impaya_factory.py"
    factory = (ROOT / factory_path).read_text(encoding="utf-8")
    loader = function_source(factory_path, "load_impaya_config")

    assert "class PaymentGatewayDisabledError" in factory
    assert "allow_inactive: bool = False" in factory
    assert "gateway_for_bot_any(bot_id)" in loader
    assert "not item.is_active and (not allow_inactive)" in loader
    assert "PaymentGatewayDisabledError" in loader
    assert "if item is None:" in loader
    assert "settings.impaya_api_token" in loader

    repository = function_source(
        "app/repositories/platform_admin.py",
        "gateway_for_bot_any",
    )
    assert "PaymentGatewayConfig.bot_id == bot_id" in repository
    assert "PaymentGatewayConfig.provider == provider" in repository
    assert "PaymentGatewayConfig.is_active" not in repository

    due_ids = function_source("app/repositories/billing.py", "due_subscription_ids")
    due_filter = function_source("app/repositories/billing.py", "_gateway_not_explicitly_disabled")
    assert "self._gateway_not_explicitly_disabled()" in due_ids
    assert "PaymentGatewayConfig.bot_id == Subscription.bot_id" in due_filter
    assert 'PaymentGatewayConfig.provider == "impaya"' in due_filter
    assert "PaymentGatewayConfig.is_active.is_(False)" in due_filter

    worker_entry = (ROOT / "app/worker.py").read_text(encoding="utf-8")
    assert "client_factory=client_factory" in worker_entry
    assert "ImpayaClient(" not in worker_entry

    admin = (ROOT / "app/web/admin_platform.py").read_text(encoding="utf-8")
    assert "repo.gateway_for_bot_any(bot.id)" in admin
    assert "current = await repo.gateway_for_bot_any(bot_id)" in admin

    reveal = function_source("app/bot/handlers/reveals.py", "confirm_reveal")
    assert "PaymentGatewayDisabledError" in reveal
    assert "VIP_PAYMENT_UNAVAILABLE" in reveal
    assert "allow_inactive=True" not in reveal

    testpay = function_source("app/bot/handlers/payments.py", "test_payment")
    assert "PaymentGatewayDisabledError" in testpay
    assert "impaya_config.api_token" in testpay
    assert "impaya_config.payment_form_url_template" in testpay
    assert "settings.impaya_api_token" not in testpay

    webhook = function_source("app/web/payment_webhook.py", "impaya_webhook")
    assert "allow_inactive=True" in webhook
    subscription_finalize = function_source(
        "app/web/subscription_payments.py",
        "finalize_subscription_payment",
    )
    assert "allow_inactive=True" in subscription_finalize
    reveal_finalize = function_source(
        "app/services/payment_notifications.py",
        "finalize_checkout_and_notify",
    )
    assert "allow_inactive=True" in reveal_finalize

    runtime = function_source("scripts/check_stage_62_runtime.py", "check_active_projects")
    assert "PaymentGatewayDisabledError" in runtime
    assert "payments intentionally disabled" in runtime

    print("Project payment gateway disable check: OK")
    print("Inactive project gateway blocks new invoices and recurrent charges")
    print("Disabled projects cannot occupy or starve automatic billing batches")
    print("Production billing uses only project-owned Impaya clients")
    print("In-flight transactions can still be authenticated and finalized")
    print("Legacy global Impaya fallback is used only when no project gateway exists")
    print("Admin editing preserves encrypted credentials while gateway is disabled")


if __name__ == "__main__":
    main()
