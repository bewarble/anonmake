# Stage 38.3 — Billing and VIP isolation

This stage isolates VIP subscriptions, saved payment methods, payment attempts
and traffic sources by bot instance.

Existing records are backfilled from their users and subscriptions. Existing
traffic sources are assigned to the primary bot.

Production rollout of additional bot containers remains disabled until the
Compose and admin-filter stage.
