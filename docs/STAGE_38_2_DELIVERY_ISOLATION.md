# Stage 38.2 — Delivery and broadcast isolation

This stage routes durable Telegram deliveries through the token configured for
the job's `bot_id`.

Configuration keeps the existing single-bot variables and adds an optional
mapping:

```env
BOT_CODE=primary
BOT_TOKEN=primary-token
MULTIBOT_TOKENS_JSON={"secondary":"secondary-token"}
```

The second bot service is still intentionally disabled. Payment notifications,
billing operations and web-admin filtering are completed in later stages.
