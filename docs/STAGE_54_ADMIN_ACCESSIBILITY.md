# Stage 54 — Admin accessibility

Stage 54 improves keyboard and assistive-technology usability across the admin UI.

- Adds a skip link to the main content.
- Adds consistent `:focus-visible` treatment for keyboard navigation.
- Exposes current navigation state with `aria-current`.
- Adds accessible labels and dialog metadata to command/search UI.
- Makes horizontally scrollable tables keyboard-focusable and labelled.
- Adds a Tab focus trap to the Stage 51 confirmation dialog while keeping Escape/cancel focus restoration.
- Adds `aria-live` to flash messages.
- Respects `prefers-reduced-motion` by disabling nonessential animations and smooth scrolling.
- Decorative icons are hidden from assistive technologies where practical.
- No database migration is required.

Run `make stage54-check` and `make release-check` before deployment.
