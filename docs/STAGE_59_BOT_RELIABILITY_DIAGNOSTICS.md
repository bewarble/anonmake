# Stage 59 — Bot reliability and diagnostics

Stage 59 expands bot observability across every bot instance without adding a database migration.

## Scope

- Every unhandled Telegram update error receives a public-safe `error_id`.
- Users see a short fallback with the diagnostic code instead of exception text.
- `bot_error` events are persisted in the existing `admin_audit_logs` storage.
- Events include bot/project context, Telegram user/chat IDs, update ID/type and request ID.
- Exception messages, tracebacks, tokens, passwords and secrets are not stored in bot-error details.
- `/testpay` no longer returns `str(exc)` to Telegram; failures are logged by `error_id`.
- Unexpected delivery-worker failures receive an `error_id`; the delivery row keeps only a safe diagnostic marker.
- Managed bot runtime crashes are recorded and surfaced before the runtime is restarted.
- `/admin/platform/observability` displays recent bot errors for all projects next to admin, delivery and payment diagnostics.

## Storage

Stage 59 reuses `admin_audit_logs` with action `bot_error`. No migration is required.

## Release gate

Run:

```bash
make stage59-check
make release-check
make docker-up
make release-check-runtime
```
