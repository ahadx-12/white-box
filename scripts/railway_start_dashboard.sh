#!/usr/bin/env bash
set -euo pipefail
cd apps/dashboard
exec npm run start -- -p "${PORT:-3000}"
