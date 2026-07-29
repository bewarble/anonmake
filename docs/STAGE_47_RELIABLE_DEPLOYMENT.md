# Stage 47 — Надёжный деплой и эксплуатация

Stage 47 добавляет управляемую команду `make deploy` и страницу
`/admin/platform/system`.

Порядок деплоя:

1. проверка чистоты Git и статических release-check;
2. проверка Docker Compose;
3. резервная копия PostgreSQL в `backups/deploy`;
4. сборка выбранных сервисов;
5. применение Alembic-миграций;
6. пересоздание сервисов;
7. ожидание `/health`;
8. runtime release-check;
9. запись отчёта в `var/deploy-state.json` и `var/deploy-history.jsonl`.

По умолчанию обновляются `web`, `worker`, `delivery-worker`,
`broadcast-worker` и `managed-bots`. Состав можно изменить:

```bash
python3 -m scripts.deploy --services web worker
```

Для аварийного деплоя с незакоммиченными изменениями существует
`--allow-dirty`, но его не следует использовать в штатной работе.
