# Stage 48 — Observability and stability

Stage 48 adds operational visibility without changing the database schema.

## Worker liveness

`delivery-worker` and `broadcast-worker` now publish heartbeat files from their real processing loops. Docker healthchecks validate both heartbeat freshness and PostgreSQL connectivity, so a container that is merely running but no longer processing work becomes unhealthy.

## Observability center

Superadmins get `/admin/platform/observability` with:

- delivery queue status counts;
- the oldest pending/processing delivery;
- recent failed Telegram delivery jobs;
- recent payment errors;
- failed deployment history;
- manual retry for failed delivery jobs;
- recovery of stale delivery locks older than five minutes.

The retry and stale-lock actions are intentionally limited to superadmins.

## Deployment impact

No Alembic migration is required. Rebuild and recreate `web`, `delivery-worker`, and `broadcast-worker` so the new routes and healthchecks are present in the running images.

After deployment verify:

```bash
make release-check
make release-check-runtime

docker compose \
  -f compose.yaml \
  -f compose.backup.yaml \
  -f compose.delivery.yaml \
  -f compose.marketing.yaml \
  --profile multibot ps
```

`delivery-worker` and `broadcast-worker` should report `healthy` after their start periods.
