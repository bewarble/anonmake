# Stage 38.1 — MultiBot foundation

This stage adds the safe identity and database foundation for multiple bots.

It intentionally does not start four bot containers yet. Delivery, broadcasts,
payments and web analytics still need bot-aware routing before that is safe.

Included:

- `bot_instances`;
- `users.bot_id`;
- uniqueness by bot and Telegram user;
- uniqueness by bot and public code;
- automatic migration of existing users to the primary bot;
- `BOT_CODE` and `BOT_DISPLAY_NAME`;
- per-update bot context;
- bot-scoped user repository lookups.
