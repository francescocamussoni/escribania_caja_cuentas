#!/bin/sh
set -eu

cd /app

alembic upgrade head
python -m app.bootstrap_production

exec "$@"
