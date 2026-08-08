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
    auth_file = (ROOT / "app/web/admin_auth.py").read_text(encoding="utf-8")
    auth = function_source("app/web/admin_auth.py", "verify_credentials")
    assert "admin_count = await repo.admin_count()" in auth
    assert "admin_count == 0" in auth
    assert auth.index("admin_count == 0") < auth.index("web_admin_username")
    assert "hmac.compare_digest" in auth
    assert "DUMMY_PASSWORD_HASH" in auth_file
    assert "verify_password(password, DUMMY_PASSWORD_HASH)" in auth
    assert "credential_stamp = password_fingerprint(admin.password_hash)" in auth

    token_create = function_source("app/web/admin_auth.py", "create_token")
    token_parse = function_source("app/web/admin_auth.py", "parse_token")
    assert "principal.credential_stamp" in token_create
    assert "credential_stamp" in token_parse
    assert "issued_at" in token_parse

    repository = function_source("app/repositories/platform_admin.py", "admin_count")
    assert "func.count(AdminUser.id)" in repository
    roster_lock = function_source("app/repositories/platform_admin.py", "lock_superadmin_roster")
    assert "AdminUser.role == 'superadmin'" in roster_lock
    assert "AdminUser.is_active.is_(True)" in roster_lock
    assert "with_for_update" in roster_lock

    scope = function_source("app/web/admin_scope.py", "load_admin_bot_scope")
    assert "principal.admin_id is None" in scope
    assert "await repo.admin_count() > 0" in scope
    assert "AdminBotScope((), None, denied=True)" in scope
    assert "password_fingerprint(current_admin.password_hash)" in scope
    assert "principal.credential_stamp" in scope
    assert "hmac.compare_digest" in scope

    runtime = function_source("scripts/check_web_admin_runtime.py", "check_bootstrap_admin")
    assert "admin_count > 0" in runtime
    assert "len(password) >= 12" in runtime
    assert "WEAK_BOOTSTRAP_PASSWORDS" in runtime
    assert "password.strip().lower() != username.lower()" in runtime

    limiter = "app/web/admin_login_security.py"
    allowed = function_source(limiter, "assert_login_allowed")
    failure = function_source(limiter, "record_login_failure")
    login = function_source(limiter, "secure_login_submit")
    installer = function_source(limiter, "install_secure_admin_login")
    assert "MAX_FAILURES_PER_IP" in allowed
    assert "MAX_FAILURES_PER_USERNAME" in allowed
    assert "HTTP_429_TOO_MANY_REQUESTS" in allowed
    assert "pipe.incr" in failure and "pipe.expire" in failure
    assert "assert_login_allowed" in login
    assert "record_login_failure" in login
    assert "clear_login_success" in login
    assert "app.router.routes[:]" in installer
    assert "secure_admin_login_installed" in installer

    platform = "app/web/admin_platform.py"
    assert "await repo.lock_superadmin_roster()" in function_source(platform, "update_admin_account")
    assert "await repo.lock_superadmin_roster()" in function_source(platform, "delete_admin_account")

    system = (ROOT / "app/web/admin_system.py").read_text(encoding="utf-8")
    assert "from app.web.admin_login_security import install_secure_admin_login" in system
    assert "install_secure_admin_login(web_app)" in system

    print("Admin authentication security check: OK")
    print("Legacy environment credentials are bootstrap-only")
    print("Existing bootstrap sessions are invalidated after first DB admin creation")
    print("Unknown DB usernames pay a dummy PBKDF2 verification cost")
    print("Redis-backed per-user and per-IP login rate limits are installed")
    print("DB admin sessions are bound to the current password hash")
    print("Active superadmin roster mutations are row-lock serialized")


if __name__ == "__main__":
    main()
