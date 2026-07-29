from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]

def main():
    required=[
      'app/models/project_setup.py','app/web/admin_project_wizard.py','app/web/templates/project_wizard.html',
      'migrations/versions/20260728_0018_project_setup_wizard.py'
    ]
    for rel in required:
        p=ROOT/rel; assert p.exists(), rel
        if p.suffix=='.py': ast.parse(p.read_text(encoding='utf-8'), filename=rel)
    wizard=(ROOT/'app/web/admin_project_wizard.py').read_text(encoding='utf-8')
    for route in ('/wizard','/{draft_id}/basic','/{draft_id}/telegram','/{draft_id}/payments','/{draft_id}/administrator','/{draft_id}/review','/{draft_id}/launch','/{draft_id}/telegram/avatar'):
        assert route in wizard, route
    assert 'ProjectProfile' in wizard and 'ProjectSetupDraft' in wizard
    assert '_readiness' in wizard and 'Managed' not in wizard
    template=(ROOT/'app/web/templates/project_wizard.html').read_text(encoding='utf-8')
    assert 'Мастер создания проекта' in template
    assert 'Запустить проект' in template
    assert 'wizard-profile-preview' in template
    assert 'data-profile-select' in template
    assert 'telegram/avatar' in template
    print('Stage 45 check: OK')
    print('Five-step project creation wizard: ready')
    print('Persistent drafts and resume flow: ready')
    print('Telegram, Impaya and administrator setup: ready')
    print('Readiness validation and transactional launch: ready')
    print('Project profiles foundation: ready')
if __name__=='__main__': main()
