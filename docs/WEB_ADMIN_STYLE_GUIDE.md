# AnonMake Web Administration Style Guide

## Language

- Interface language is Russian.
- Technical identifiers remain visible only in detail views.
- Raw database statuses are never used as primary labels.
- Use `VIP подписка` for the product and `VIP статус` for the user state.
- `Рефералы` are shown as `Источники`.

## Statuses

Every status has a human label and one of five tones:

- success — completed or active;
- warning — requires attention;
- danger — failed or unavailable;
- info — queued or processing;
- neutral — archived or manually disabled.

Mappings live in `app/web/admin_ui.py`.

## Components

- Every page starts with a title, short description and optional count.
- Filters always have labels and `Применить` / `Сбросить` actions.
- Empty states explain what is missing and, when useful, what to do next.
- Dangerous actions always use a confirmation page.
- Tables use the shared status badge and formatting filters.
