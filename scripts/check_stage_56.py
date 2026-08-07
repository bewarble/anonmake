from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path, *needles):
    text = (ROOT / path).read_text(encoding='utf-8')
    for needle in needles:
        assert needle in text, (path, needle)


def main():
    require(
        'app/web/static/admin-stage56.css',
        '--admin-control-height',
        '.button-primary',
        '.button-secondary',
        '.notice.success',
        '.empty-state',
        '.filter-actions',
        '@media(max-width:700px)',
    )
    require('app/web/templates/base.html', 'admin-stage56.css?v=')
    require('scripts/audit_active_web_assets.py', '"admin-stage56.css"')
    assert not list((ROOT / 'migrations/versions').glob('*stage_56*'))
    print('Stage 56 check: OK')
    print('Buttons, notices, forms, page rhythm and empty states: unified')
    print('No Stage 56 migration required')


if __name__ == '__main__':
    main()
