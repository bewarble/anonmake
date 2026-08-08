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
    auth = function_source("app/web/admin_auth.py", "verify_credentials")
    assert "admin_count = await repo.admin_count()" in auth
    assert "admin_count == 0" in auth
    assert auth.index("admin_count == 0") < auth.index("web_admin_username")
    assert "hmac.compare_digest" in auth

    repository = function_source("app/repositories/platform_admin.py", "admin_count")
    assert "func.count(AdminUser.id)" in repository

    scope = function_source("app/web/admin_scope.py", "load_admin_bot_scope")
    assert "principal.admin_id is None" in scope
    assert "await repo.admin_count() > 0" in scope
    assert "AdminBotScope((), None, denied=True)" in scope

    runtime = function_source("scripts/check_web_admin_runtime.py", "check_bootstrap_admin")
    assert "admin_count > 0" in runtime
    assert "len(password) >= 12" in runtime
    assert "WEAK_BOOTSTRAP_PASSWORDS" in runtime
    assert "password.strip().lower() != username.lower()" in runtime

    print("Admin authentication security check: OK")
    print("Legacy environment credentials are bootstrap-only")
    print("Existing bootstrap sessions are invalidated after first DB admin creation")
    print("Any DB administrator permanently disables legacy superadmin login")
    print("Bootstrap-only mode rejects weak/default superadmin passwords")


if __name__ == "__main__":
    main()
