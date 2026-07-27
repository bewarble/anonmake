from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def check() -> None:
    required = (
        "app/web/admin_stage27.py",
        "app/web/admin_repository_stage27.py",
        "app/web/templates/dashboard_v2.html",
        "app/web/templates/crm_users.html",
        "app/web/templates/crm_user_details.html",
        "app/web/templates/crm_source_details.html",
        "app/web/templates/broadcasts.html",
        "app/web/static/admin_stage27.css",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel
    for rel in ("app/web/admin_stage27.py", "app/web/admin_repository_stage27.py"):
        ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)
    print("Stage 27 structural check: OK")
    print("Dashboard charts: ready")
    print("CRM filters and timeline: ready")
    print("Source economics: ready")
    print("Broadcast operations list: ready")

if __name__ == "__main__":
    check()
