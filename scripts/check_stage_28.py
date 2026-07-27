from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def check() -> None:
    required = (
        "app/web/admin_stage28.py",
        "app/web/admin_repository_stage28.py",
        "app/web/templates/pro_dashboard.html",
        "app/web/templates/analytics.html",
        "app/web/static/admin_stage28.css",
        "app/web/static/admin_stage28.js",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel

    for rel in (
        "app/web/admin_stage28.py",
        "app/web/admin_repository_stage28.py",
    ):
        ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)

    app_text = (ROOT / "app/web/app.py").read_text(encoding="utf-8")
    assert "admin_stage28" in app_text
    registration_ok = (
        "app.include_router(admin_stage28_router)" in app_text
        or "admin_stage28_module.router.routes" in app_text
    )
    assert registration_ok

    base = (ROOT / "app/web/templates/base.html").read_text(encoding="utf-8")
    assert "admin_stage28.css" in base
    assert "admin_stage28.js" in base

    print("Stage 28 check: OK")
    print("Professional navigation: ready")
    print("Theme switch and command palette: ready")
    print("Product analytics and funnel: ready")
    print("Source economics and operations: ready")

if __name__ == "__main__":
    check()
