from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def require(path, *needles):
    text = (ROOT / path).read_text(encoding='utf-8')
    for needle in needles:
        assert needle in text, (path, needle)

def main():
    require('app/web/templates/base.html',
            'admin-skip-link', 'href="#admin-main"', 'id="admin-main"',
            'aria-label="Разделы панели управления"', 'aria-live="polite"',
            'admin-stage54.css?v=', 'admin-stage54.js?v=')
    require('app/web/static/admin-stage54.css',
            ':focus-visible', 'prefers-reduced-motion', 'admin-skip-link', 'admin-sr-only')
    require('app/web/static/admin-stage54.js',
            'aria-current', 'aria-controls', 'aria-expanded', 'aria-modal',
            "event.key !== 'Tab'", 'focusableSelector', 'Прокручиваемая таблица')
    require('app/web/static/admin-stage51.js', 'role="dialog"', 'aria-modal="true"')
    require('scripts/audit_active_web_assets.py', '"admin-stage54.css"', '"admin-stage54.js"')
    assert not list((ROOT / 'migrations/versions').glob('*stage_54*'))
    print('Stage 54 check: OK')
    print('Skip link, keyboard focus, dialog focus trap and reduced motion: ready')
    print('Navigation, command dialog, tables and flash messages expose accessibility metadata')
    print('No Stage 54 migration required')

if __name__ == '__main__':
    main()
