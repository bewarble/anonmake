# Stage 53 — Admin data states

Stage 53 unifies how admin pages explain data availability and transitions.

- shared loading indicator for filter/navigation transitions;
- distinct empty and filtered-no-results states;
- shared stale-data badge primitive for timestamped panels;
- reusable `data_state` Jinja macro;
- core user, source and delivery lists migrated to the shared states;
- mobile-friendly state actions;
- no database migration.

Run `make stage53-check` and `make release-check` before deployment.
