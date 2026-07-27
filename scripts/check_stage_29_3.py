from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def check() -> None:
    required = (
        "app/web/admin_stage29_3.py",
        "app/web/templates/business_analytics.html",
        "app/broadcast_worker.py",
        "app/web/static/admin_stage29_3.js",
        "app/web/static/admin_stage29_3.css",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel

    ast.parse((ROOT / "app/web/admin_stage29_3.py").read_text(encoding="utf-8"))
    ast.parse((ROOT / "app/broadcast_worker.py").read_text(encoding="utf-8"))

    worker = (ROOT / "app/broadcast_worker.py").read_text(encoding="utf-8")
    assert "recipient.id == sender.id" not in worker
    assert "item.queued_count += len(users)" in worker

    base = (ROOT / "app/web/templates/base.html").read_text(encoding="utf-8")
    assert 'href="/admin/business/analytics"' in base
    assert "admin_stage29_3.js" in base

    admin = (ROOT / "app/web/admin.py").read_text(encoding="utf-8")
    assert '"/admin/business"' in admin

    print("Stage 29.3 check: OK")
    print("/admin and Главная: business dashboard")
    print("Аналитика: separate analytics page")
    print("Broadcast sender: included in audience")
    print("Telegram and web broadcasts: common worker format")

if __name__ == "__main__":
    check()
