# Stage 52 — Admin form validation UX

Stage 52 adds one shared browser-side validation layer to admin forms.

- Russian inline messages for required, email, length, range and pattern errors.
- Invalid controls receive `aria-invalid` and a visible error state.
- The first invalid field receives focus and is scrolled into view.
- Errors clear as soon as the value becomes valid.
- Existing Stage 51 submit locking remains authoritative after validation succeeds.
- Native HTML constraints remain the source of truth; Stage 52 does not duplicate server business validation.
- No database migration is required.

Run `make stage52-check` and `make release-check` before deployment.
