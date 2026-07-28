# Stage 40 — Multibot Admin Control Center

The web administration now has a persistent project selector and a projects
comparison page. Selecting a bot code scopes the main business dashboard,
users and marketing sources to that bot. The selection is preserved in an
HTTP-only administration cookie and can also be shared with `?bot=<code>`.

The new `/admin/projects` page compares users, active VIP subscriptions,
revenue, delivery queue and delivery errors for every registered bot.
