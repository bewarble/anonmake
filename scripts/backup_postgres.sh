#!/bin/sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="$BACKUP_DIR/anonmake-$TIMESTAMP.sql.gz"
TMP="$FILE.tmp"

mkdir -p "$BACKUP_DIR"

PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
  --host=db \
  --username="${POSTGRES_USER:-anonmake}" \
  --dbname="${POSTGRES_DB:-anonmake}" \
  --format=plain \
  --no-owner \
  --no-privileges \
  | gzip -9 > "$TMP"

gzip -t "$TMP"
mv "$TMP" "$FILE"

find "$BACKUP_DIR" -type f -name 'anonmake-*.sql.gz' \
  -mtime "+$RETENTION_DAYS" -delete

echo "Backup created: $FILE"
