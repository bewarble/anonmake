from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "app/web"

EXPECTED = {
    "/admin/business",
    "/admin/business/analytics",
    "/admin/business/users",
    "/admin/business/sources",
    "/admin/business/broadcasts",
    "/admin/subscriptions",
    "/admin/payments",
    "/admin/delivery",
    "/admin/audit",
    "/admin/crm/users/{user_id}",
    "/admin/crm/users/{user_id}/control",
}


def source_routes(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    routes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            func = decorator.func
            if not isinstance(func, ast.Attribute) or func.attr not in {"get", "post", "put", "delete", "patch"}:
                continue
            first = decorator.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                value = first.value
                if value.startswith("/admin"):
                    routes.add(value)
                elif value.startswith("/"):
                    routes.add("/admin" + value)
    return routes


def check() -> None:
    routes: set[str] = set()
    for path in WEB.glob("admin*.py"):
        routes |= source_routes(path)
    missing = EXPECTED - routes
    if missing:
        raise AssertionError("Missing admin routes: " + ", ".join(sorted(missing)))
    print("Admin route registry audit: OK")
    print("Required sections:", len(EXPECTED))


if __name__ == "__main__":
    check()
