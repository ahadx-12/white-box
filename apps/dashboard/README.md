# TrustAI Dashboard

## Local development

```bash
npm install
npm run dev
```

### Environment

Set the API base URL for the dashboard:

```bash
export NEXT_PUBLIC_TRUSTAI_API_BASE=http://localhost:8000
```

The dashboard will ping `/v1/health` on load to show API status.

## Build

```bash
npm run build
npm run start
```
