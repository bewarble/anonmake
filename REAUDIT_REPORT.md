# Production re-audit

This pass reviewed the cleaned project again and applied additional fixes.

## Fixed

- removed duplicate, unused BI/statistics implementation;
- removed unused system-health and metrics modules;
- hardened all marketing FSM handlers with admin checks and stale-state handling;
- added length and numeric validation for traffic sources;
- changed source deletion to archival so historical attribution is preserved;
- ensured only active traffic sources are listed;
- validated broadcast kind, audience and text in the repository layer;
- avoided database writes before forwarding personal `/start` links;
- preserved real Telegram retry errors in the delivery outbox;
- added row locking for due billing subscriptions;
- prevented a reveal purchase from shortening existing VIP access;
- required an Impaya webhook secret whenever billing is enabled;
- changed `/health` to verify the database;
- cleaned duplicated `.gitignore` rules;
- made Redis rate-limit counters atomic and closed the shared Redis client on shutdown;
- made delivery enqueue work with PostgreSQL and local SQLite;
- expanded `scripts.check_project` with import, router, security and cleanup checks;
- connected previously ignored billing price/duration environment settings;
- fixed stale Makefile checks and standardized commands on the full Compose stack;
- fixed backup error handling so a failed `pg_dump` cannot produce a false successful backup.

## Operational note

The code was statically parsed and project-level checks were executed. Live
Impaya, Telegram and PostgreSQL integration still require container tests in
the deployment environment because those external services are unavailable
inside the audit environment.
