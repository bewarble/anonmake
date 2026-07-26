#!/bin/sh
set -eu

# Database migrations are executed by the dedicated Compose `migrate` service.
# Keeping migrations out of every container prevents concurrent Alembic runs.
exec "$@"
