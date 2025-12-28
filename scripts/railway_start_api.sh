#!/usr/bin/env bash
set -euo pipefail
exec uvicorn trustai_api.main:create_app --factory --app-dir apps/api/src --host 0.0.0.0 --port "${PORT:-8000}"
