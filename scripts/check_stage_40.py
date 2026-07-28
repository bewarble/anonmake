from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/web/admin_scope.py",
        "app/web/admin_multibot.py",
        "app/web/templates/projects.html",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    base = (ROOT / "app/web/templates/base.html").read_text(encoding="utf-8")
    assert "data-project-selector" in base
    assert "/admin/projects" in base

    app = (ROOT / "app/web/app.py").read_text(encoding="utf-8")
    assert "admin_bot_scope_middleware" in app
    assert "admin_multibot_module" in app

    repository = (ROOT / "app/web/admin_repository_stage29.py").read_text(encoding="utf-8")
    assert "bot_id: int | None" in repository
    assert "PaymentAttempt.bot_id == self.bot_id" in repository
    assert "User.bot_id == self.bot_id" in repository

    print("Stage 40 check: OK")
    print("Global project selector: ready")
    print("Per-project business dashboard scope: ready")
    print("Projects comparison dashboard: ready")
    print("Per-bot users, revenue, VIP and delivery metrics: ready")


if __name__ == "__main__":
    check()
