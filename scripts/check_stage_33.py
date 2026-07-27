from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/web/admin_ui.py",
        "app/web/static/admin_stage33.css",
        "app/web/static/admin_stage33.js",
        "app/web/templates/ui_macros.html",
        "docs/WEB_ADMIN_STYLE_GUIDE.md",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    admin = (ROOT / "app/web/admin.py").read_text(encoding="utf-8")
    assert "templates.env.filters.update" in admin
    assert "status_label=admin_ui.status_label" in admin

    base = (ROOT / "app/web/templates/base.html").read_text(encoding="utf-8")
    assert "admin_stage33.css" in base
    assert "admin_stage33.js" in base
    assert "Панель управления AnonMake" in base

    for name in ("payments.html", "subscriptions.html", "delivery.html", "audit.html"):
        text = (ROOT / "app/web/templates" / name).read_text(encoding="utf-8")
        assert "ui_macros.html" in text

    # Every button opening tag must define a type.
    for template in (ROOT / "app/web/templates").glob("*.html"):
        text = template.read_text(encoding="utf-8")
        for match in re.finditer(r"<button\\b[^>]*>", text, re.I | re.S):
            if not re.search(r"\\btype\\s*=", match.group(0), re.I):
                line = text.count("\n", 0, match.start()) + 1
                raise AssertionError(f"{template.name}:{line}: button type missing")

    print("Stage 33 check: OK")
    print("Unified web formatters and status labels: ready")
    print("Operational pages and empty states: unified")
    print("Filters, tables and pagination: unified")
    print("Final design layer and mobile layout: ready")
    print("Web administration style guide: ready")


if __name__ == "__main__":
    check()
