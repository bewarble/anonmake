# Release preparation

## Static checks

```bash
python3 -m scripts.release_check
```

These checks do not require running PostgreSQL or Redis.

## Runtime checks

Run inside the Docker Compose network:

```bash
docker compose \
  -f compose.yaml \
  -f compose.backup.yaml \
  -f compose.delivery.yaml \
  -f compose.marketing.yaml \
  exec -T web python -m scripts.release_check --runtime
```

Runtime mode checks:

- PostgreSQL connectivity;
- Redis connectivity;
- Alembic migration head;
- web administration runtime.

## Cleanup preview

```bash
python3 -m scripts.stabilize_project
```

## Cleanup with rollback archive

```bash
python3 -m scripts.stabilize_project --apply
```
