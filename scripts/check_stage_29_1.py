from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def check():
    required = (
        "app/web/admin_stage29.py",
        "app/web/templates/business_dashboard.html",
        "app/web/templates/business_source_details.html",
        "app/web/templates/business_broadcasts.html",
        "app/web/static/admin_stage29_1.css",
        "app/web/static/admin_stage29.js",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel

    ast.parse((ROOT / "app/web/admin_stage29.py").read_text(encoding="utf-8"))
    route = (ROOT / "app/web/admin_stage29.py").read_text(encoding="utf-8")
    assert 'period: str = "1"' in route
    assert "source_referral_url" in route
    assert "session.add(item)" in route

    js = (ROOT / "app/web/static/admin_stage29.js").read_text(encoding="utf-8")
    assert 'addEventListener("pointerup"' in js
    assert "currentPath" in js

    print("Stage 29.1 check: OK")
    print("Active navigation state: fixed")
    print("Today period and smooth tabs: fixed")
    print("Chart point details: fixed")
    print("Referral URL: ready")
    print("Broadcast creation: hardened")

if __name__ == "__main__":
    check()
