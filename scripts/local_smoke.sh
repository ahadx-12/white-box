#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
PACK="${PACK:-general}"
export TRUSTAI_LLM_MODE="${TRUSTAI_LLM_MODE:-mock}"

PYTHONPATH="apps/api/src:packages/core/src" uvicorn trustai_api.main:create_app --factory --app-dir apps/api/src --host 127.0.0.1 --port 8000 &
UVICORN_PID=$!

cleanup() {
  kill "$UVICORN_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in {1..30}; do
  if curl -sf "${BASE_URL}/v1/health" >/dev/null; then
    break
  fi
  sleep 1
done

python scripts/railway_smoke.py --base-url "${BASE_URL}" --pack "${PACK}"
