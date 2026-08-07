from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app/web/templates"
STATIC = ROOT / "app/web/static"
ACTIVE_ASSETS = {
    "admin-ui.css",
    "admin-ui.js",
    "admin-stage50.css",
    "admin-stage51.css",
    "admin-stage51.js",
}


def referenced_assets() -> set[str]:
    found: set[str] = set()
    pattern = re.compile(r'/admin/static/([^"?]+)')
    for template in TEMPLATES.glob("*.html"):
        found.update(pattern.findall(template.read_text(encoding="utf-8")))
    return found


def main() -> None:
    references = referenced_assets()
    missing = [name for name in sorted(references) if not (STATIC / name).is_file()]
    assert not missing, missing

    unexpected = references - ACTIVE_ASSETS
    missing_active = ACTIVE_ASSETS - references
    assert not unexpected, unexpected
    assert not missing_active, missing_active

    legacy = sorted(
        path.name
        for path in STATIC.glob("admin_stage*")
        if path.is_file()
    )

    print("Active web asset audit: OK")
    print("Active assets:", ", ".join(sorted(references)))
    print("Compatibility assets retained:", len(legacy))
    print(
        "Legacy files are no longer loaded and may be removed in the release stage "
        "after the final visual edits."
    )


if __name__ == "__main__":
    main()
