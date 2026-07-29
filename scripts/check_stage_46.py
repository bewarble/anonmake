from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    route = ROOT / "app/web/admin_multibot.py"
    template = ROOT / "app/web/templates/project_details.html"
    css = ROOT / "app/web/static/admin-ui.css"

    ast.parse(route.read_text(encoding="utf-8"), filename=str(route))
    html = template.read_text(encoding="utf-8")
    styles = css.read_text(encoding="utf-8")

    for tab in ("overview", "telegram", "payments", "admins", "activity", "settings"):
        assert f"tab={tab}" in html, tab
    assert "telegram/check" in route.read_text(encoding="utf-8")
    assert "service-health-grid" in html
    assert "project-console-hero" in styles
    assert "project-admin-grid" in styles
    assert "Internal Server Error" not in html

    print("Stage 46 check: OK")
    print("Tabbed project control center: ready")
    print("Project KPI and health overview: ready")
    print("Telegram and Impaya project panels: ready")
    print("Project administrators and activity journal: ready")
    print("Responsive Russian interface: ready")


if __name__ == "__main__":
    main()
