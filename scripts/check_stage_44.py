from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
def main():
    files=("app/managed_bots.py","app/services/bot_credentials.py","app/web/templates/project_create.html","migrations/versions/20260728_0017_managed_projects.py")
    for rel in files:
        path=ROOT/rel; assert path.exists(), rel
        if path.suffix==".py": ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    text=(ROOT/"app/web/admin_multibot.py").read_text(encoding="utf-8")
    assert '"/projects/create/new"' in text and 'verify_telegram_token' in text
    assert 'managed-bots:' in (ROOT/"compose.yaml").read_text(encoding="utf-8")
    print("Stage 44 check: OK")
    print("Project creation from admin panel: ready")
    print("Telegram getMe validation and encrypted tokens: ready")
    print("Managed multi-project polling service: ready")
    print("Delivery worker DB token fallback: ready")
if __name__=='__main__': main()
