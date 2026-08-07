# Stage 58 — Bot UX and navigation

Stage 58 gives the Telegram bot a predictable home/navigation layer without changing billing or message-delivery logic.

## User-facing behavior

- Ordinary `/start` shows a short welcome and installs the main reply keyboard.
- The personal link is still shown with its existing share button.
- The user menu contains `🔗 Моя ссылка` and `❓ Помощь`.
- `/menu` clears an active FSM flow and returns to the main menu.
- `/help` and the Help button show the same product help copy.
- Unsupported input outside functional flows receives a short fallback and the main menu instead of silence.
- Existing `/cancel` behavior remains the explicit cancellation action inside question/answer flows.

## Routing safety

Navigation commands are registered before FSM content handlers so `/menu` can interrupt a flow. The catch-all fallback router is registered after all functional handlers so it does not swallow questions, answers, payments, reveals, or admin actions.

## Storage

No database migration is required.
