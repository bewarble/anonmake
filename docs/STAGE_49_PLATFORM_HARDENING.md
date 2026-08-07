# Stage 49 — Platform hardening and recovery readiness

Stage 49 strengthens operational recovery without introducing destructive actions into the web admin.

## Included

- backup integrity status on `/admin/platform/system`;
- recent deploy backup inventory;
- PostgreSQL custom-format signature validation (`PGDMP`);
- safe CLI to list and verify deploy backups;
- non-destructive recovery plan generator;
- static and runtime Stage 49 release checks;
- runtime validation of the newest mounted deploy backup.

## Commands

```bash
python3 -m scripts.backup_recovery list
python3 -m scripts.backup_recovery verify <file.dump>
python3 -m scripts.backup_recovery plan <file.dump>
```

`plan` only prints an explicit recovery procedure. It never drops, restores or modifies the production database.

## Release validation

```bash
python3 -m scripts.check_stage_49
make release-check
make deploy
make release-check-runtime
```

No database migration is required for Stage 49.

## Recovery policy

A deploy backup is considered structurally recognizable when it is non-empty and starts with the PostgreSQL custom-format magic bytes `PGDMP`. This is a fast guard against empty, HTML, text or otherwise invalid files; it is not a substitute for periodically testing restore into an isolated database.
