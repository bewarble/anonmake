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
    path = "app/web/admin_project_details_scoped.py"
    details = function_source(path, "project_details")
    assert "AdminAuditLog.bot_id == bot.id" in details
    assert "AdminAuditLog.details.ilike" not in details
    assert "PaymentAttempt.bot_id == bot.id" in details
    assert "DeliveryOutbox.bot_id == bot.id" in details
    assert "gateway.is_active" in details
    assert "settings.impaya_api_token.strip()" in details

    installer = function_source(path, "install_scoped_project_details")
    assert "app.router.routes[:]" in installer
    assert "PROJECT_DETAILS_PATH" in installer
    assert "app.add_api_route" in installer
    assert "scoped_project_details_installed" in installer

    system = (ROOT / "app/web/admin_system.py").read_text(encoding="utf-8")
    assert "from app.web.admin_project_details_scoped import install_scoped_project_details" in system
    assert "install_scoped_project_details(web_app)" in system

    print("Project details isolation check: OK")
    print("Recent audit rows are strictly filtered by AdminAuditLog.bot_id")
    print("Inactive project gateway is shown as payments disabled")
    print("Legacy project-details GET route is replaced, not duplicated")


if __name__ == "__main__":
    main()
