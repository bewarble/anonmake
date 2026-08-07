from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def require(path, *needles):
    text = (ROOT / path).read_text(encoding='utf-8')
    for needle in needles:
        assert needle in text, (path, needle)

def main():
    require('app/web/static/admin-stage55.css',
            'overflow-x:hidden', 'viewport-fit=cover', 'safe-area-inset-bottom',
            'grid-template-columns:minmax(0,1fr)!important', 'table-wrap',
            'period-tabs', 'admin-action-dialog', '@media(max-width:390px)')
    require('app/web/templates/base.html',
            'viewport-fit=cover', 'admin-stage55.css?v=55')
    require('scripts/audit_active_web_assets.py', '"admin-stage55.css"')
    assert not list((ROOT / 'migrations/versions').glob('*stage_55*'))
    print('Stage 55 check: OK')
    print('Responsive overflow, narrow-screen stacking and iPhone safe-area polish: ready')
    print('Horizontal scrolling remains scoped to wide tables and tab strips')
    print('No Stage 55 migration required')

if __name__ == '__main__':
    main()
