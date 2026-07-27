from __future__ import annotations

from app.web.app import app


def check() -> None:
    paths = {
        getattr(route, "path", "")
        for route in app.routes
    }

    required = {
        "/admin",
        "/admin/",
        "/admin/login",
        "/admin/users",
        "/admin/users/{user_id}",
        "/admin/payments",
        "/admin/sources",
        "/admin/delivery",
        "/admin/audit",
        "/health",
        "/metrics",
        "/payments/impaya/webhook",
    }
    missing = required - paths
    assert not missing, sorted(missing)

    print("Stage 26.1 runtime check: OK")
    print(f"Routes registered: {len(paths)}")
    print("Web admin and payment routes coexist")


if __name__ == "__main__":
    check()
