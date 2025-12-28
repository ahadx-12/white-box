# TrustAI API

FastAPI service that exposes verification endpoints and persists proofs/jobs.

## Quick start

```bash
uvicorn trustai_api.main:create_app --factory --reload
```

Environment variables:
- `DATABASE_URL` (default: Postgres in docker)
- `REDIS_URL`
- `TRUSTAI_PACKS_ROOT` (default: storage/packs)
- `OPENAI_MODEL`
- `CLAUDE_MODEL`
- `TRUSTAI_DB_AUTOCREATE` (default: 1)
