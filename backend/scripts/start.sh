#!/bin/sh
# Production entrypoint (Render / any PaaS).
#
# Two jobs, in order:
#   1. alembic upgrade head  -> apply any pending migrations before serving.
#      (On ECS this is a separate one-shot task; on a single free-tier
#      service, running it at boot is the simplest safe pattern.)
#   2. uvicorn on $PORT      -> PaaS platforms inject PORT; default 8000
#      keeps the same script working locally and in Compose.
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting API on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
