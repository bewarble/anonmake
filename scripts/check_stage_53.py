from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def require(path, *needles):
    text=(ROOT/path).read_text(encoding='utf-8')
    for needle in needles: assert needle in text,(path,needle)

def main():
    require('app/web/static/admin-stage53.js','admin-page-loading','data-data-filter','data-stale-after','is-data-loading','pageshow')
    require('app/web/static/admin-stage53.css','admin-data-state','admin-page-loading','admin-stale-badge','stage53-loading')
    require('app/web/templates/ui_macros.html','macro data_state','admin-data-state','data-data-nav')
    require('app/web/templates/base.html','admin-stage53.css?v=','admin-stage53.js?v=')
    require('app/web/templates/business_users.html','data-data-filter','По фильтрам ничего не найдено','Сбросить фильтры')
    require('app/web/templates/business_sources.html','Источников пока нет','Создать источник')
    require('app/web/templates/delivery.html','Очередь пуста','data-data-scope')
    require('scripts/audit_active_web_assets.py','"admin-stage53.css"','"admin-stage53.js"')
    assert not list((ROOT/'migrations/versions').glob('*stage_53*'))
    print('Stage 53 check: OK')
    print('Loading, empty, no-results and stale-state primitives: ready')
    print('Core user/source/delivery lists use unified data states')
    print('No Stage 53 migration required')

if __name__=='__main__': main()
