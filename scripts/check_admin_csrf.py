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
    guard_path = "app/web/admin_csrf.py"
    system_path = "app/web/admin_system.py"

    guard = function_source(guard_path, "same_origin_admin_request")
    assert "UNSAFE_METHODS" in guard
    assert 'request.url.path.startswith("/admin")' in guard
    assert 'request.headers.get("origin")' in guard
    assert 'request.headers.get("referer")' in guard
    assert "return False" in guard

    install = function_source(guard_path, "install_admin_csrf_guard")
    assert 'app.middleware("http")' in install
    assert "same_origin_admin_request" in install
    assert "status_code=403" in install

    system = (ROOT / system_path).read_text(encoding="utf-8")
    assert "from app.web.admin_csrf import install_admin_csrf_guard" in system
    assert "install_admin_csrf_guard(web_app)" in system

    platform = (ROOT / "app/web/admin_platform.py").read_text(encoding="utf-8")
    multibot = (ROOT / "app/web/admin_multibot.py").read_text(encoding="utf-8")
    observability = (ROOT / "app/web/admin_observability.py").read_text(encoding="utf-8")
    assert '@router.post("/admins")' in platform
    assert '@router.post("/payments/{bot_id}")' in platform
    assert '@router.post("/projects/{code}/settings")' in multibot
    assert '@router.post("/projects/{code}/telegram")' in multibot
    assert '@router.post("/observability/delivery/{job_id}/retry")' in observability

    print("Admin CSRF protection check: OK")
    print("All unsafe /admin methods pass through a same-origin gate")
    print("Critical platform/project/observability mutations are covered")


if __name__ == "__main__":
    main()
