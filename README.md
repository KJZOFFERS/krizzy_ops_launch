# KRIZZY OPS Web (Single-Service)

One web process with FastAPI + Uvicorn. Healthcheck at `/health`. Optional Discord + Airtable KPI logging (safe no-op if envs missing).

## Quick start (Railway)

1) Create project → Add service (from repo or template).
2) Add **variables** from `.env.example`:
   - AIRTABLE_API_KEY, AIRTABLE_BASE_ID (if you want KPI logging)
   - DISCORD_WEBHOOK_OPS, DISCORD_WEBHOOK_ERRORS (optional)
   - SERVICE_NAME=krizzy_ops_web
   - ENV=production
3) Confirm **Procfile** is detected and `railway.json` healthcheck is `/health`.
4) Deploy. Service is healthy when GET `/health` returns:
   ```json
   {"status":"healthy","service":"krizzy_ops_web"}
