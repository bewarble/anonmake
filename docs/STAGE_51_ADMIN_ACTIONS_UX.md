# Stage 51 — Admin actions UX

Stage 51 standardizes interactive admin actions without changing the database schema.

## Scope

- shared confirmation dialog for sensitive or bulk POST actions;
- replacement of browser `confirm()` prompts with the admin UI language and styling;
- loading labels and visual busy state while POST requests are being submitted;
- compatibility with the existing repeat-submit protection in `admin-ui.js`;
- Escape/backdrop cancellation and focus return for confirmation dialogs;
- mobile-friendly confirmation layout;
- explicit confirmation for administrator account removal;
- explicit confirmation for bulk stale delivery unlock;
- loading state for delivery retry and account creation/removal;
- Stage 51 static checker and release-check integration.

## Confirmation contract

A POST form opts into confirmation with `data-confirm`. Optional attributes are:

- `data-confirm-title` — dialog title;
- `data-confirm-label` — confirmation button label;
- `data-confirm-tone="danger"` — destructive visual tone;
- `data-loading-label` — text displayed while the request is being submitted.

Forms without `data-confirm` submit normally and still receive the common busy state.

## Safety

The confirmation layer does not execute actions through JavaScript APIs. After confirmation it re-submits the original HTML form with `requestSubmit`, so server-side routing, validation, permissions and CSRF-related behavior remain authoritative.

No database migration is required.

## Verification

```bash
make stage51-check
make release-check
```

Runtime smoke test: open `/admin/platform/admins`, trigger account removal without confirming, then cancel; open `/admin/platform/observability`, trigger stale delivery unlock, cancel, then verify a safe POST action shows a busy state only once.
