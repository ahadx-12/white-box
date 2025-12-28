# Railway Deployment Guide

This repo is a monorepo with three Railway services:

- **trustai-api** (FastAPI)
- **trustai-worker** (RQ worker)
- **trustai-dashboard** (Next.js)

## 1) Create the Railway project + plugins

1. Create a new Railway project from this repo.
2. Add the **Postgres** plugin.
3. Add the **Redis** plugin.

## 2) Create services from the same repo

### A) trustai-api

- **Root Directory**: `/`
- **Config Path**: `/apps/api/railway.json`
- **Attach plugins**: Postgres + Redis
- **Environment variables**:
  - `TRUSTAI_DB_AUTOCREATE=1`
  - `OPENAI_API_KEY=...`
  - `ANTHROPIC_API_KEY=...`
  - (optional) `OPENAI_MODEL`, `CLAUDE_MODEL`, `TRUSTAI_PACKS_ROOT`
- **Networking**: expose a public domain (Railway will generate one)

### B) trustai-worker

- **Root Directory**: `/`
- **Config Path**: `/apps/worker/railway.json`
- **Attach plugins**: Redis
- **Networking**: no public domain required

### C) trustai-dashboard

- **Root Directory**: `/apps/dashboard`
- **Config Path**: `/apps/dashboard/railway.json`
- **Environment variables**:
  - `NEXT_PUBLIC_TRUSTAI_API_BASE=https://<trustai-api-domain>`
- **Networking**: expose a public domain

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

Async verify (requires worker + Redis):

```bash
JOB_ID=$(curl -sSf "https://<trustai-api-domain>/v1/verify?mode=async" \
  -H "Content-Type: application/json" \
  -H "X-TrustAI-Pack: general" \
  -d '{"input":"The sky is blue."}' | jq -r .job_id)

curl -sSf "https://<trustai-api-domain>/v1/jobs/${JOB_ID}"
```
