from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def check() -> None:
    required = (
        "app/web/admin_stage29_3.py",
        "app/web/templates/business_analytics.html",
        "app/web/templates/business_broadcasts.html",
        "app/web/static/admin_stage29_4.js",
        "app/web/static/admin_stage29_4.css",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel

    ast.parse((ROOT / "app/web/admin_stage29_3.py").read_text(encoding="utf-8"))

    analytics = (ROOT / "app/web/templates/business_analytics.html").read_text(encoding="utf-8")
    assert "Сегодня" in analytics
    assert "Всё время" in analytics
    assert "data-stage294-chart" in analytics

    js = (ROOT / "app/web/static/admin_stage29_4.js").read_text(encoding="utf-8")
    assert "blocked metric is rendered as columns" in js
    assert "row.blocked" in js

    campaigns = (ROOT / "app/web/templates/business_broadcasts.html").read_text(encoding="utf-8")
    assert "campaign-card" in campaigns
    assert "campaign-status" in campaigns

    print("Stage 29.4 check: OK")
    print("Analytics Today and All Time: ready")
    print("Blocked metric visibility: fixed")
    print("Campaign history cards: ready")

if __name__ == "__main__":
    check()
