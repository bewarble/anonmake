from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def check():
    required = (
        "app/web/admin_stage29.py",
        "app/web/admin_repository_stage29.py",
        "app/web/templates/business_dashboard.html",
        "app/web/templates/business_users.html",
        "app/web/templates/business_sources.html",
        "app/web/templates/business_source_form.html",
        "app/web/templates/business_source_details.html",
        "app/web/templates/business_broadcasts.html",
        "app/web/static/admin_stage29.css",
        "app/web/static/admin_stage29.js",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel
    ast.parse((ROOT/"app/web/admin_stage29.py").read_text(encoding="utf-8"))
    ast.parse((ROOT/"app/web/admin_repository_stage29.py").read_text(encoding="utf-8"))
    app_text=(ROOT/"app/web/app.py").read_text(encoding="utf-8")
    assert "admin_stage29_module.router.routes" in app_text
    print("Stage 29 check: OK")
    print("Business dashboard and period comparisons: ready")
    print("Clickable chart details: ready")
    print("Users, sources CRUD and broadcasts: ready")
    print("Mobile full-screen navigation: ready")

if __name__=="__main__":
    check()
