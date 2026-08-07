# Stage 58 — Bot UX and navigation

Stage 58 gives the Telegram bot a predictable home/navigation layer without changing billing or message-delivery logic.

## User-facing behavior

- `/start` is the single home command.
- Ordinary `/start` clears an active FSM flow, shows the personal link, and installs the main reply keyboard.
- The personal link keeps its existing inline share button.
- The user menu contains `🔗 Моя ссылка` and `❓ Помощь`.
- Help is opened from the reply keyboard, without advertising extra slash commands.
- Unsupported input outside functional flows receives a short fallback and the main menu instead of silence.
- `/cancel` is reserved for subscription auto-renew cancellation; question/answer flows use their inline cancel action instead.

## Routing safety

`/start` is registered before FSM content handlers so it can always return the user home. The catch-all fallback router is registered after all functional handlers so it does not swallow questions, answers, payments, reveals, or admin actions.

## Storage

No database migration is required.
