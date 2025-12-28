#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}

note() {
  echo "[smoke] $1"
}

if ! command -v docker >/dev/null 2>&1; then
  note "skipping (docker not available)"
  exit 0
fi

if ! curl -sf "${BASE_URL}/v1/health" > /dev/null; then
  note "skipping (api not running at ${BASE_URL})"
  exit 0
fi

note "Checking health"
curl -sf "${BASE_URL}/v1/health" > /dev/null

note "Listing packs"
PACKS_JSON=$(curl -sf "${BASE_URL}/v1/packs")
DEFAULT_PACK=$(PACKS_JSON="${PACKS_JSON}" python - <<'PY'
import json, os
packs = json.loads(os.environ["PACKS_JSON"])["packs"]
print(packs[0] if packs else "general")
PY
)

note "Running sync verify"
SYNC_JSON=$(curl -sf -X POST "${BASE_URL}/v1/verify" \
  -H "Content-Type: application/json" \
  -H "X-TrustAI-Pack: ${DEFAULT_PACK}" \
  -d '{"input":"What is 2+2?"}')
SYNC_JSON="${SYNC_JSON}" python - <<'PY'
import json, os
payload = json.loads(os.environ["SYNC_JSON"])
assert payload["status"] in {"verified", "failed"}
assert payload.get("proof_id")
print("sync ok")
PY

note "Running async verify"
ASYNC_JSON=$(curl -sf -X POST "${BASE_URL}/v1/verify?mode=async" \
  -H "Content-Type: application/json" \
  -H "X-TrustAI-Pack: ${DEFAULT_PACK}" \
  -d '{"input":"Explain why A kills B differs from B kills A"}')
JOB_ID=$(ASYNC_JSON="${ASYNC_JSON}" python - <<'PY'
import json, os
payload = json.loads(os.environ["ASYNC_JSON"])
print(payload["job_id"])
PY
)

note "Polling job ${JOB_ID}"
for _ in {1..60}; do
  JOB_JSON=$(curl -sf "${BASE_URL}/v1/jobs/${JOB_ID}")
  STATUS=$(JOB_JSON="${JOB_JSON}" python - <<'PY'
import json, os
payload = json.loads(os.environ["JOB_JSON"])
print(payload.get("status"))
PY
)
  if [[ "${STATUS}" == "done" ]]; then
    JOB_JSON="${JOB_JSON}" python - <<'PY'
import json, os
payload = json.loads(os.environ["JOB_JSON"])
result = payload.get("result")
assert result
assert result.get("proof_id")
print("async ok")
PY
    exit 0
  fi
  if [[ "${STATUS}" == "failed" ]]; then
    echo "Job failed"
    exit 1
  fi
  sleep 1
  done

echo "Timed out waiting for job"
exit 1
