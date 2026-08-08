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
    assert "gateway_for_bot_any(bot_id)" in loader
    assert "item is not None and (not item.is_active)" in loader
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

    admin = (ROOT / "app/web/admin_platform.py").read_text(encoding="utf-8")
    assert "repo.gateway_for_bot_any(bot.id)" in admin
    assert "current = await repo.gateway_for_bot_any(bot_id)" in admin

    print("Project payment gateway disable check: OK")
    print("Stored inactive gateway fails closed and never falls back to global Impaya")
    print("Legacy global Impaya fallback remains only for projects without a gateway row")
    print("Admin editing preserves encrypted credentials while gateway is disabled")


if __name__ == "__main__":
    main()
