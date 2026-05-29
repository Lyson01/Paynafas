#!/usr/bin/env sh
set -eu

alembic upgrade head

uvicorn app.web.main:app \
  --host "${WEBAPP_HOST:-0.0.0.0}" \
  --port "${PORT:-${WEBAPP_PORT:-8000}}" &

python -m app.main
