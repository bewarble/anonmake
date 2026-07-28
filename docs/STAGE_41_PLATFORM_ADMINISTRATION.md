# Stage 41 — Platform Administration

Stage 41 introduces database-backed administrator accounts and separate Impaya
configuration for every bot project.

Roles:

- `superadmin`: access to every project and platform settings;
- `project_admin`: access only to explicitly assigned bot projects.

The legacy WEB_ADMIN_USERNAME / WEB_ADMIN_PASSWORD login remains as a bootstrap
SuperAdmin account until database accounts are created.

Impaya API tokens and webhook secrets are encrypted using a key derived from
WEB_ADMIN_SECRET. Changing WEB_ADMIN_SECRET after saving gateway credentials
will make the stored secrets unreadable.
