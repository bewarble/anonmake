#!/bin/sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="$BACKUP_DIR/anonmake-$TIMESTAMP.sql.gz"
TMP_SQL="$BACKUP_DIR/.anonmake-$TIMESTAMP.sql.tmp"
TMP_GZ="$FILE.tmp"

cleanup() {
  rm -f "$TMP_SQL" "$TMP_GZ"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$BACKUP_DIR"

PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
  --host=db \
  --username="${POSTGRES_USER:-anonmake}" \
  --dbname="${POSTGRES_DB:-anonmake}" \
  --format=plain \
  --no-owner \
  --no-privileges \
  --file="$TMP_SQL"

gzip -9 -c "$TMP_SQL" > "$TMP_GZ"
gzip -t "$TMP_GZ"
mv "$TMP_GZ" "$FILE"
rm -f "$TMP_SQL"
trap - EXIT HUP INT TERM

find "$BACKUP_DIR" -type f -name 'anonmake-*.sql.gz' \
  -mtime "+$RETENTION_DAYS" -delete

echo "Backup created: $FILE"
