# Stage 38.4 — Four-bot rollout

This stage adds three profile-gated polling services alongside the
existing primary `bot` service:

- `bot`
- `bot-two`
- `bot-three`
- `bot-four`

PostgreSQL, Redis, the web application and all workers remain shared.

## Safety

The default Compose startup still runs only the primary bot. Additional
bots are enabled explicitly with the `multibot` profile after their
tokens and usernames have been configured.

## Required environment variables

Configure `BOT_TWO_*`, `BOT_THREE_*` and `BOT_FOUR_*` in `.env`.
Codes and usernames must be unique. Tokens are never stored in the
database.

## Start

```bash
docker compose \
  -f compose.yaml \
  -f compose.backup.yaml \
  -f compose.delivery.yaml \
  -f compose.marketing.yaml \
  --profile multibot \
  up -d bot bot-two bot-three bot-four
```

## Stop secondary bots

```bash
docker compose \
  -f compose.yaml \
  -f compose.backup.yaml \
  -f compose.delivery.yaml \
  -f compose.marketing.yaml \
  --profile multibot \
  stop bot-two bot-three bot-four
```
