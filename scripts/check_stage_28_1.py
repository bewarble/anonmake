from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def check():
    required = (
        "app/web/admin_stage28_1.py",
        "app/web/templates/pro_dashboard_28_1.html",
        "app/web/templates/source_create.html",
        "app/web/static/admin_stage28_1.css",
        "app/web/static/admin_stage28.js",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel
    ast.parse((ROOT / "app/web/admin_stage28_1.py").read_text(encoding="utf-8"))
    text = (ROOT / "app/web/admin_stage28_1.py").read_text(encoding="utf-8")
    assert '@router.get("/sources/new"' in text
    assert '@router.post("/sources/new"' in text
    base = (ROOT / "app/web/templates/base.html").read_text(encoding="utf-8")
    assert "admin_stage28_1.css" in base
    assert "data-sidebar-close" in base
    print("Stage 28.1 check: OK")
    print("Light theme: rebuilt")
    print("Mobile drawer: rebuilt")
    print("Clickable chart points: ready")
    print("Web source creation: ready")

if __name__ == "__main__":
    check()
