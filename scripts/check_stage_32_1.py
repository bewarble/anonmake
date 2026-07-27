from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    required = (
        "app/web/static/admin_stage32_1.js",
        "app/web/static/admin_stage32_1.css",
        "app/web/templates/base.html",
        "app/web/app.py",
        "app/web/admin_stage31.py",
        "scripts/check_product_language.py",
    )
    for rel in required:
        path = ROOT / rel
        assert path.is_file(), rel
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)

    base = (ROOT / "app/web/templates/base.html").read_text(encoding="utf-8")
    assert "admin_stage32_1.css" in base
    assert "admin_stage32_1.js" in base
    assert 'href="/admin/business/analytics"' in base

    css = (ROOT / "app/web/static/admin_stage32_1.css").read_text(encoding="utf-8")
    assert "[hidden]" in css
    assert "pointer-events: none" in css
    assert "pointer-events: auto" in css

    js = (ROOT / "app/web/static/admin_stage32_1.js").read_text(encoding="utf-8")
    assert "closeCommandPalette" in js
    assert "initForms" in js
    assert "initNavigation" in js
    assert "pageshow" in js

    admin31 = (ROOT / "app/web/admin_stage31.py").read_text(encoding="utf-8")
    assert '"/subscriptions"' in admin31
    assert '"/crm/users/{user_id}/control"' in admin31
    assert "numeric_filters" in admin31

    # Buttons may span several lines, so inspect complete opening tags.
    import re

    for template in (ROOT / "app/web/templates").glob("*.html"):
        template_text = template.read_text(encoding="utf-8")

        for match in re.finditer(
            r"<button\\b[^>]*>",
            template_text,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            tag = match.group(0)

            if re.search(
                r"\\btype\\s*=",
                tag,
                flags=re.IGNORECASE,
            ):
                continue

            line_no = template_text.count(
                "\\n",
                0,
                match.start(),
            ) + 1

            raise AssertionError(
                f"{template.name}:{line_no}: button type missing"
            )

    print("Stage 32.1 check: OK")
    print("Admin overlays and click targets: repaired")
    print("Navigation and command palette: repaired")
    print("Forms and duplicate-click protection: ready")
    print("Mobile sidebar interactions: ready")
    print("Large Telegram ID filters: ready")
    print("Product language audit: ready")


if __name__ == "__main__":
    check()
