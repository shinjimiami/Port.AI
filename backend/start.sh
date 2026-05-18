#!/usr/bin/env bash
set -e

echo "Running database migrations…"
alembic upgrade head

echo "Starting API server…"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --log-level info
