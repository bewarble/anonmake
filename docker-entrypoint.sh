#!/bin/sh
set -eu

python -m scripts.migrate
exec "$@"
