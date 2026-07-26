# AnonMake code audit

## Fixed

- Removed six release ZIP files and temporary stage backups from the repository.
- Removed disabled Telegram admin implementations and duplicate keyboards.
- Rebuilt the router registry around the current compact admin surface.
- Fixed the referral callback regular expression (`adminm:source:<id>`).
- Removed duplicate source-detail and legacy broadcast routes.
- Added authorization checks and safe ID parsing to administrative callbacks.
- Preserved the administrator keyboard after question/answer flows.
- Reformatted configuration and application entrypoint without changing environment names.
- Added `scripts/check_project.py` for repeatable structural verification.

## Deliberately retained

- CRM models and event tracking: they are used by product analytics even though the Telegram CRM UI was removed.
- Delivery outbox and delivery worker: production-critical reliability layer.
- Billing, Impaya, webhook and billing worker code: payment integration is paused, not deleted.
- `AdminBIService`: still supplies daily revenue points for the active profit chart.
- Historical Alembic migrations: never delete applied migrations from a live project.

## Runtime checks still required on the server

1. Build all Docker services.
2. Run Alembic migration-head validation.
3. Run `python -m scripts.check_project` in the bot image.
4. Test `/start`, personal deep links, questions, answers and reveals.
5. Test Statistics, Profit, Export, Referrals and Broadcast.
6. Inspect bot, delivery-worker, broadcast-worker and web logs.
