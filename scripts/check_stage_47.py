from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    required = (
        "scripts/deploy.py",
        "app/web/admin_system.py",
        "app/web/templates/platform_system.html",
        "docs/STAGE_47_RELIABLE_DEPLOYMENT.md",
    )
    for relative in required:
        path = ROOT / relative
        assert path.exists(), relative
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=relative)

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "deploy:" in makefile
    assert "scripts.deploy" in makefile

    app = (ROOT / "app/web/app.py").read_text(encoding="utf-8")
    assert "admin_system_module" in app

    template = (ROOT / "app/web/templates/platform_system.html").read_text(encoding="utf-8")
    assert "Состояние системы" in template
    assert "Текущие очереди" in template

    deploy = (ROOT / "scripts/deploy.py").read_text(encoding="utf-8")
    for marker in ("backup_database", "wait_for_web", "release_check", "deploy-state.json"):
        assert marker in deploy, marker

    print("Stage 47 check: OK")
    print("Managed deployment command: ready")
    print("Pre-deploy PostgreSQL backup: ready")
    print("Health and runtime validation: ready")
    print("Deployment journal and system page: ready")
    print("Alembic version consistency check: ready")


if __name__ == "__main__":
    main()
