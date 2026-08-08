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
    model = (ROOT / "app/models/admin.py").read_text(encoding="utf-8")
    assert "bot_id: Mapped[int | None]" in model
    assert 'ForeignKey("bot_instances.id", ondelete="SET NULL")' in model

    migration = (ROOT / "migrations/versions/20260808_0026_admin_audit_bot_id.py").read_text(encoding="utf-8")
    assert 'revision = "20260808_0026"' in migration
    assert 'down_revision = "20260808_0025"' in migration
    assert '"admin_audit_logs"' in migration
    assert '"bot_id"' in migration

    telegram_audit = function_source("app/repositories/admin.py", "audit")
    assert "bot_id=bot.id" in telegram_audit.replace(" ", "")
    recent = function_source("app/repositories/admin.py", "recent_audit")
    assert "AdminAuditLog.bot_id == bot.id" in recent
    assert "details.like" not in recent

    bot_error = function_source("app/core/error_diagnostics.py", "record_bot_error")
    assert "bot_id=bot.id if bot else None" in bot_error.replace(" ", "")

    web_error = function_source("app/web/admin_error_ux.py", "record_admin_error")
    assert "bot_id=bot_id" in web_error.replace(" ", "")

    support = function_source("app/services/admin_subscription_control.py", "_audit")
    assert "bot_id=bot.id" in support.replace(" ", "")

    page = function_source("app/web/admin_audit_scoped.py", "audit_page")
    assert "AdminAuditLog.bot_id == bot_id" in page
    assert "not principal.is_superadmin" in page
    installer = function_source("app/web/admin_audit_scoped.py", "install_scoped_admin_audit")
    assert "app.router.routes[:]" in installer
    assert "AUDIT_PATH" in installer
    assert "app.add_api_route" in installer

    system = (ROOT / "app/web/admin_system.py").read_text(encoding="utf-8")
    assert "install_scoped_admin_audit(web_app)" in system

    print("Admin audit project isolation check: OK")
    print("New audit events persist explicit bot ownership")
    print("Project audit view filters by AdminAuditLog.bot_id")
    print("Legacy NULL/platform audit rows are not exposed to project scope")


if __name__ == "__main__":
    main()
