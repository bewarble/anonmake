#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: restore_postgres.sh /backups/anonmake-*.sql.gz" >&2
  exit 1
fi

FILE="$1"
test -f "$FILE"
gzip -t "$FILE"

if [ "${CONFIRM_RESTORE:-}" != "yes" ]; then
  echo "Set CONFIRM_RESTORE=yes to continue." >&2
  exit 2
fi

PGPASSWORD="$POSTGRES_PASSWORD" dropdb \
  --host=db \
  --username="${POSTGRES_USER:-anonmake}" \
  --if-exists "${POSTGRES_DB:-anonmake}"

PGPASSWORD="$POSTGRES_PASSWORD" createdb \
  --host=db \
  --username="${POSTGRES_USER:-anonmake}" \
  "${POSTGRES_DB:-anonmake}"

gzip -dc "$FILE" | PGPASSWORD="$POSTGRES_PASSWORD" psql \
  --host=db \
  --username="${POSTGRES_USER:-anonmake}" \
  --dbname="${POSTGRES_DB:-anonmake}" \
  --set=ON_ERROR_STOP=1

echo "Database restored successfully."
