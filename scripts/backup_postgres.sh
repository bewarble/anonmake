#!/bin/sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="$BACKUP_DIR/anonmake-$TIMESTAMP.dump"
TMP="$FILE.tmp"

cleanup() {
  rm -f "$TMP"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$BACKUP_DIR"

PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
  --host=db \
  --username="${POSTGRES_USER:-anonmake}" \
  --dbname="${POSTGRES_DB:-anonmake}" \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file="$TMP"

# A zero-length/truncated file is not a backup. pg_restore --list parses the
# custom archive directory without changing any database and catches corrupt
# or incomplete dumps before they are promoted to the final filename.
PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --list "$TMP" >/dev/null

MAGIC="$(dd if="$TMP" bs=1 count=5 2>/dev/null || true)"
if [ "$MAGIC" != "PGDMP" ]; then
  echo "Backup validation failed: PostgreSQL custom header is missing" >&2
  exit 1
fi

mv "$TMP" "$FILE"
trap - EXIT HUP INT TERM

find "$BACKUP_DIR" -type f -name 'anonmake-*.dump' \
  -mtime "+$RETENTION_DAYS" -delete

echo "Backup created: $FILE"
