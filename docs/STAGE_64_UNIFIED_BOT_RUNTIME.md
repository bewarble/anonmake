# Stage 64 — Unified Bot Runtime

## Goal

Run every Telegram project through one `managed-bots` Docker service. Adding or updating a bot in the admin panel must not require a new Compose service or a server-side `.env` edit when an encrypted credential is stored in the database.

## Runtime contract

- `managed-bots` owns polling for every active `BotInstance` with `runtime_mode=managed`.
- `bot`, `bot-two`, `bot-three`, and `bot-four` Compose polling services are removed.
- Existing environment tokens remain a credential fallback for legacy projects during migration.
- Encrypted tokens stored from the admin panel have priority over environment credentials.
- Token changes are detected by fingerprint and restart only the affected in-process bot task.
- Each bot receives an isolated router tree and Redis FSM namespace.
- `docker-up` and managed deploy use `--remove-orphans` so old per-bot containers disappear after rollout.

## Migration

`20260808_0025_unified_bot_runtime.py` changes all existing `bot_instances.runtime_mode` values to `managed` and makes `managed` the database default.

## Operational result

A fifth, tenth, or hundredth bot can be added in the admin panel without changing Docker Compose. The number of Telegram projects no longer equals the number of Docker polling containers.
