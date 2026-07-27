# Stage 34 — Stabilization

This stage intentionally adds no product features.

## Removed from the working repository

- `.stage*-install` directories;
- historical stage backup directories;
- historical audit backup directories;
- temporary `*.bak-before-*` files;
- temporary `.env.before-*` files;
- release ZIP files stored in the project root;
- local `anonmake.db`;
- generated historical audit reports;
- Python bytecode caches.

Before deletion, `scripts/stabilize_project.py --apply` creates a compressed
rollback archive outside the repository in:

```text
../anonmake-stabilization-backups/
```

## Not removed

Stage-named runtime modules and web assets remain in place because they are
still imported or referenced by templates. They are reported by
`scripts.audit_codebase` and can be renamed during the next visual refactor.

No database schema or production data is changed.
