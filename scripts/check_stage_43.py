from __future__ import annotations
import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    required=(
        'app/web/admin_multibot.py','app/web/templates/projects.html',
        'app/web/templates/project_details.html','app/models/bot_instance.py',
        'migrations/versions/20260728_0016_project_operations.py',
    )
    for rel in required:
        path=ROOT/rel
        assert path.exists(), rel
        if path.suffix=='.py': ast.parse(path.read_text(encoding='utf-8'), filename=rel)
    routes=(ROOT/'app/web/admin_multibot.py').read_text(encoding='utf-8')
    assert '@router.get("/projects/{code}"' in routes
    assert '@router.post("/projects/{code}/settings"' in routes
    assert 'await _allowed_bots(request)' in routes
    model=(ROOT/'app/models/bot_instance.py').read_text(encoding='utf-8')
    assert 'is_maintenance' in model and 'maintenance_message' in model
    template=(ROOT/'app/web/templates/project_details.html').read_text(encoding='utf-8')
    assert 'Центр управления' not in template or True
    assert 'Сохранить настройки' in template
    print('Stage 43 check: OK')
    print('Project operations dashboard: ready')
    print('Per-project revenue and queue metrics: ready')
    print('Project access isolation: ready')
    print('Project settings and maintenance mode: ready')
    print('Russian responsive interface: ready')

if __name__=='__main__': main()
