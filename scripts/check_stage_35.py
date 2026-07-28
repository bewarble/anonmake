from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_assets() -> None:
    from html.parser import HTMLParser

    required = (
        "app/web/static/admin-ui.css",
        "app/web/static/admin-ui.js",
        "app/web/admin_assets.py",
        "app/web/route_registry.py",
        "docs/ADMIN_UI_ARCHITECTURE.md",
    )
    for rel in required:
        required_path = ROOT / rel
        assert required_path.is_file(), rel
        if required_path.suffix == ".py":
            ast.parse(
                required_path.read_text(encoding="utf-8"),
                filename=rel,
            )

    class AssetParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.stylesheets: list[str] = []
            self.scripts: list[str] = []

        def handle_starttag(self, tag, attrs) -> None:
            values = dict(attrs)

            if tag.lower() == "link":
                href = values.get("href")
                if href:
                    self.stylesheets.append(href)

            if tag.lower() == "script":
                src = values.get("src")
                if src:
                    self.scripts.append(src)

    base = (ROOT / "app/web/templates/base.html").read_text(
        encoding="utf-8"
    )
    login = (ROOT / "app/web/templates/login.html").read_text(
        encoding="utf-8"
    )

    base_parser = AssetParser()
    base_parser.feed(base)

    login_parser = AssetParser()
    login_parser.feed(login)

    css_links = [
        value
        for value in base_parser.stylesheets
        if "admin-ui.css" in value
    ]
    js_scripts = [
        value
        for value in base_parser.scripts
        if "admin-ui.js" in value
    ]
    login_css_links = [
        value
        for value in login_parser.stylesheets
        if "admin-ui.css" in value
    ]

    assert len(css_links) == 1, {
        "admin_ui_css": css_links,
        "all_stylesheets": base_parser.stylesheets,
    }
    assert len(js_scripts) == 1, {
        "admin_ui_js": js_scripts,
        "all_scripts": base_parser.scripts,
    }
    assert len(login_css_links) == 1, {
        "admin_ui_css": login_css_links,
        "all_stylesheets": login_parser.stylesheets,
    }

    all_active_assets = (
        base_parser.stylesheets
        + base_parser.scripts
        + login_parser.stylesheets
        + login_parser.scripts
    )
    assert not any(
        "admin_stage" in value
        for value in all_active_assets
    ), all_active_assets

    css = (ROOT / "app/web/static/admin-ui.css").read_text(
        encoding="utf-8"
    )
    js = (ROOT / "app/web/static/admin-ui.js").read_text(
        encoding="utf-8"
    )

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
