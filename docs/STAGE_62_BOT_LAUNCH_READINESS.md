# Stage 62 — Bot Launch Readiness

Stage 62 is the final user-facing Telegram bot hardening pass before public launch.

## Public UX contract

- `/start` is the single canonical entry point and always restores the main user UX.
- Marketing `src_...` payloads only record attribution; the same `/start` handler renders the welcome, persistent menu, personal link and share button.
- Telegram's public command list contains only `/start` and `/cancel`.
- `/cancel` is reserved exclusively for disabling subscription auto-renewal, even if an input FSM is active.
- The `⬅️ Отмена` inline button cancels the current question/answer input flow.
- Unknown or stale inline callbacks always stop the Telegram spinner and show a safe recovery message.
- One anonymous message may receive unlimited replies.

## Payment/reveal hardening

- Repeated reveal-confirm taps reuse an existing pending invoice instead of creating duplicate payment intents.
- An already-active VIP user is revealed immediately when returning to an old consent button.
- Reveal payment finalization always resolves the current bot context before creating billing records.
- Repeated delete/edit callback actions treat Telegram's benign `message is not modified`/old-message cases as normal user behavior.
- Test payment handlers remain behind `PAYMENT_TEST_COMMANDS_ENABLED=false` for launch runtime.

## Checks

`make stage62-check` validates the code contract.

`make release-check-runtime` validates the live primary bot command list and launch-safe runtime flags.

`make launch-check` is the strict final gate before public traffic. In addition to all release checks it requires production billing, automatic renewal, HTTPS public URLs, disabled payment-test commands, and non-stage/non-test Impaya endpoint and terminals.
