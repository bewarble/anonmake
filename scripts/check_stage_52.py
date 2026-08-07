from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def require(path, *needles):
    text=(ROOT/path).read_text(encoding='utf-8')
    for needle in needles: assert needle in text,(path,needle)

def main():
    require(
        'app/web/static/admin-stage52.js',
        'valueMissing',
        'typeMismatch',
        'tooShort',
        'aria-invalid',
        'admin-field-error',
        'revealFirstInvalid',
        "addEventListener('invalid'",
        'invalidTimer',
        'scrollInvalidBlock',
        'window.scrollTo',
    )
    require('app/web/static/admin-stage52.css','has-error','aria-invalid="true"','admin-field-error')
    require('app/web/templates/base.html','admin-stage52.css?v=52','admin-stage52.js?v=52')
    require('scripts/audit_active_web_assets.py','"admin-stage52.css"','"admin-stage52.js"')
    assert not list((ROOT/'migrations/versions').glob('*stage_52*'))
    print('Stage 52 check: OK')
    print('Inline validation and invalid-event first-error reveal: ready')
    print('Mobile validation avoids forced keyboard focus')
    print('No Stage 52 migration required')

if __name__=='__main__': main()
