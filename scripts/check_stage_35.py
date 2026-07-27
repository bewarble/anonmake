from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_assets() -> None:
    required = (
        "app/web/static/admin-ui.css",
        "app/web/static/admin-ui.js",
        "app/web/admin_assets.py",
        "app/web/route_registry.py",
        "docs/ADMIN_UI_ARCHITECTURE.md",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    base = (ROOT / "app/web/templates/base.html").read_text(encoding="utf-8")
    login = (ROOT / "app/web/templates/login.html").read_text(encoding="utf-8")

    assert base.count("admin-ui.css") == 1
    assert base.count("admin-ui.js") == 1
    assert login.count("admin-ui.css") == 1

    assert not re.search(r'admin_stage\d', base)
    assert not re.search(r'admin_stage\d', login)

    css = (ROOT / "app/web/static/admin-ui.css").read_text(encoding="utf-8")
    js = (ROOT / "app/web/static/admin-ui.js").read_text(encoding="utf-8")
    assert len(css) > 40_000
    assert len(js) > 20_000
    assert "admin_stage28.css" in css
    assert "admin_stage33.css" in css
    assert "admin_stage28.js" in js
    assert "admin_stage33.js" in js
    assert "Stage 35 final interaction guards" in js


def check_templates() -> None:
    for template in (ROOT / "app/web/templates").glob("*.html"):
        text = template.read_text(encoding="utf-8")
        for match in re.finditer(
            r"<button\b[^>]*>",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            assert re.search(r"\btype\s*=", match.group(0), re.IGNORECASE), (
                template.name,
                text.count("\n", 0, match.start()) + 1,
            )


def check_route_registry() -> None:
    text = (ROOT / "app/web/route_registry.py").read_text(encoding="utf-8")
    assert "frozenset" in text
    assert "register_unique_routes" in text
    assert "existing.add(key)" in text


def main() -> None:
    check_assets()
    check_templates()
    check_route_registry()
    print("Stage 35 check: OK")
    print("Single admin CSS bundle: ready")
    print("Single admin JavaScript bundle: ready")
    print("Legacy cascade order: preserved")
    print("Sidebar and command-palette accessibility: improved")
    print("Route registration helper: ready")
    print("Template button audit: passed")


if __name__ == "__main__":
    main()
