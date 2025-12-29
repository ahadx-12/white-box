# Railway Deployment Guide

This repo is a monorepo with three Railway services:

- **trustai-api** (FastAPI)
- **trustai-worker** (RQ worker)
- **trustai-dashboard** (Next.js)

## 1) Create the Railway project + plugins

1. Create a new Railway project from this repo.
2. Add the **Postgres** plugin.
3. Add the **Redis** plugin.

## 2) Create services from the same repo (no guess setup)

> **Why this exists:** Railway sometimes ignores nested `railway.json`. The root
> entrypoint (`main.py`) plus explicit start commands guarantee a stable deploy.

### A) trustai-api

- **Root Directory**: `/`
- **Build Command**:
  - `python -m pip install --upgrade pip && python -m pip install -r requirements.txt`
- **Start Command (choose ONE)**:
  - `TRUSTAI_SERVICE=api python main.py`
  - `bash scripts/railway_start_api.sh`
- **Healthcheck path**: `/v1/health`
- **Attach plugins**: Postgres + Redis
- **Environment variables**:
  - `TRUSTAI_SERVICE=api`
  - `TRUSTAI_LLM_MODE=live`
  - `OPENAI_API_KEY=...` (or `OPEN_AI_KEY`)
  - `ANTHROPIC_API_KEY=...` (or `CLAUD_AI_KEY`)
  - `TRUSTAI_ANTHROPIC_MODEL=...` (optional preferred Claude model)
  - `TRUSTAI_ANTHROPIC_MODEL_FALLBACKS=...` (optional comma-separated fallbacks)
  - `DATABASE_URL` (from Postgres plugin)
  - `REDIS_URL` (from Redis plugin)
  - `TRUSTAI_DB_AUTOCREATE=1`
  - `TRUSTAI_THRESHOLD=0.92`
  - `TRUSTAI_MAX_ITERS=5`
  - (optional) `OPENAI_MODEL`, `CLAUDE_MODEL`, `TRUSTAI_PACKS_ROOT`, `TRUSTAI_DEBUG_DEFAULT`, `TRUSTAI_CORS_ORIGINS`
- **Networking**: expose a public domain (Railway will generate one)

### B) trustai-worker

- **Root Directory**: `/`
- **Build Command**:
  - `python -m pip install --upgrade pip && python -m pip install -r requirements.txt`
- **Start Command (choose ONE)**:
  - `TRUSTAI_SERVICE=worker python main.py`
  - `bash scripts/railway_start_worker.sh`
- **Attach plugins**: Redis
- **Environment variables**:
  - `TRUSTAI_SERVICE=worker`
  - `TRUSTAI_LLM_MODE=live`
  - `OPENAI_API_KEY=...` (or `OPEN_AI_KEY`)
  - `ANTHROPIC_API_KEY=...` (or `CLAUD_AI_KEY`)
  - `TRUSTAI_ANTHROPIC_MODEL=...` (optional preferred Claude model)
  - `TRUSTAI_ANTHROPIC_MODEL_FALLBACKS=...` (optional comma-separated fallbacks)
  - `DATABASE_URL`
  - `REDIS_URL`
- **Networking**: no public domain required

### C) trustai-dashboard

- **Root Directory**: `apps/dashboard`
- **Build Command**:
  - `npm ci && npm run build`
- **Start Command (choose ONE)**:
  - `npm run start -- -p $PORT`
  - `bash ../scripts/railway_start_dashboard.sh`
- **Environment variables**:
  - `NEXT_PUBLIC_TRUSTAI_API_BASE=https://<trustai-api-domain>`
- **Networking**: expose a public domain

## Where is my dashboard URL?

Use the public domain Railway assigns to the **trustai-dashboard** service. The
dashboard lives at the root path (`/`). API docs are served by the API service at
`/docs` (e.g. `https://<trustai-api-domain>/docs`).

## 3) Post-deploy verification

Run these against the API public domain:

```bash
curl -sSf https://<trustai-api-domain>/v1/health
curl -sSf https://<trustai-api-domain>/v1/packs
```

Sync verify:

```bash
curl -sSf https://<trustai-api-domain>/v1/verify \
  -H "Content-Type: application/json" \
  -H "X-TrustAI-Pack: general" \
  -d '{"input":"The sky is blue."}'
```

Smoke script:

```bash
python scripts/railway_live_smoke.py --base-url https://<trustai-api-domain> --pack general
```

## 4) Live convergence runbook (Railway)

Required env vars for API + worker:

- `TRUSTAI_LLM_MODE=live`
- `OPENAI_API_KEY=...` (or `OPEN_AI_KEY`)
- `ANTHROPIC_API_KEY=...` (or `CLAUD_AI_KEY`)
- `TRUSTAI_ANTHROPIC_MODEL=...` (optional preferred Claude model)
- `TRUSTAI_ANTHROPIC_MODEL_FALLBACKS=...` (optional comma-separated fallbacks)
- `DATABASE_URL` (from Railway Postgres plugin)
- `REDIS_URL` (from Railway Redis plugin)

Optional:

- `TRUSTAI_DB_AUTOCREATE=1`
- `TRUSTAI_THRESHOLD=0.92`
- `TRUSTAI_MAX_ITERS=5`
- `TRUSTAI_DEBUG_DEFAULT=0`

Once deployed, run the live convergence harness against the public API domain:

```bash
python scripts/live_convergence.py --base-url https://<trustai-api-domain> --pack general
```

Expected behavior:

- Iteration 1 is often rejected with conflicts/unsupported claims.
- Iteration 2+ converges with improved similarity and corrected answers.

Async verify (requires worker + Redis):

```bash
JOB_ID=$(curl -sSf "https://<trustai-api-domain>/v1/verify?mode=async" \
  -H "Content-Type: application/json" \
  -H "X-TrustAI-Pack: general" \
  -d '{"input":"The sky is blue."}' | jq -r .job_id)

curl -sSf "https://<trustai-api-domain>/v1/jobs/${JOB_ID}"
```
