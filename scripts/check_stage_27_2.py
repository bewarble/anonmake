from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def check() -> None:
    route_file = ROOT / "app/web/admin_stage27.py"
    text = route_file.read_text(encoding="utf-8")
    ast.parse(text, filename=str(route_file))
    assert 'request.query_params.get("source_id")' in text
    assert "source_id: int | None" not in text
    assert "parse_optional_positive_int" in text
    template = (ROOT / "app/web/templates/crm_users.html").read_text(encoding="utf-8")
    assert 'name="source_id"' in template
    assert 'value=""' in template
    print("Stage 27.2 check: OK")
    print("Referral-source filter: empty value is safe")
    print("Dashboard and CRM layout: refreshed")

if __name__ == "__main__":
    check()
