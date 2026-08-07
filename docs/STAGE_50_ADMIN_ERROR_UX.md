# Stage 50 — Admin error UX and diagnostics

Stage 50 replaces raw admin errors with a consistent, safe operator experience and keeps diagnostics inside the existing audit storage.

## Included

- styled admin error pages for 403, 404, 409, 422 and 500;
- opaque `error_id` values generated for admin error responses;
- safe `web_error` events in `admin_audit_logs` with route, HTTP method, admin identity, project scope and status;
- no traceback, exception text, request body, cookies, tokens or secrets stored in the admin error event;
- recent admin errors on `/admin/platform/observability`;
- copy button for the 500 error identifier;
- admin-only response safety middleware that converts raw JSON/plain-text admin errors into HTML;
- global flash notification presentation and helpers for post-action redirects;
- Stage 50 static checker;
- no database migration.

## Storage policy

Stage 50 reuses `admin_audit_logs`. Error rows use:

- `action = web_error`;
- `target = <error_id>`;
- `details =` compact JSON containing only `status`, `method`, `route`, `admin`, `admin_id`, `project` and `project_id`.

The original Python exception is written only to the server log for 500 diagnostics. It is never rendered into the browser and is never copied into the audit row.

## Flash UX

New action redirects should use `redirect_with_flash()` from `app.web.admin_error_ux`. The base admin template renders `flash` and `flash_tone` query parameters in a common notification component.

## Validation

```bash
python3 -m scripts.check_stage_50
make stage50-check
make release-check
```

No Alembic migration is required for Stage 50.
