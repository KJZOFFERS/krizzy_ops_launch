# src/app.py
# KRIZZY OPS - FastAPI + 24/7 Scheduler

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from typing import Dict, Any


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: launch scheduler
    from src.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    
    yield
    
    # Shutdown: stop scheduler
    stop_scheduler()


app = FastAPI(
    title="KRIZZY OPS",
    version="1.0.0",
    description="REI Dispo + GovCon Sub-Trap Automation Platform",
    lifespan=lifespan
)


@app.get("/")
def root() -> Dict[str, Any]:
    return {"krizzy_ops": "online", "scheduler": "active"}


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.get("/health/deep")
async def health_deep() -> Dict[str, Any]:
    """
    Deep health check.
    Never throws – always returns JSON with integration statuses.
    """
    results: Dict[str, Any] = {"status": "ok", "integrations": {}}

    # Airtable
    try:
        from src.common.airtable_client import get_airtable
        at = get_airtable()
        results["integrations"]["airtable"] = (
            "configured" if at is not None else "not_configured"
        )
    except Exception as e:
        results["integrations"]["airtable"] = f"error: {e}"

    # Discord
    try:
        from src.common.discord_notify import get_webhook_status
        results["integrations"]["discord"] = get_webhook_status()
    except Exception as e:
        results["integrations"]["discord"] = f"error: {e}"

    # Twilio
    try:
        from src.common.twilio_client import get_twilio
        tw = get_twilio()
        results["integrations"]["twilio"] = (
            "configured" if tw is not None else "not_configured"
        )
    except Exception as e:
        results["integrations"]["twilio"] = f"error: {e}"

    # GitHub
    try:
        from src.tools.github_client import get_github_client
        gh = get_github_client()
        results["integrations"]["github"] = (
            "configured" if gh is not None else "not_configured"
        )
    except Exception as e:
        results["integrations"]["github"] = f"error: {e}"

    # Scheduler
    try:
        from src.scheduler import scheduler, SCHEDULER_ENABLED, REI_INTERVAL, GOVCON_INTERVAL
        results["integrations"]["scheduler"] = {
            "enabled": SCHEDULER_ENABLED,
            "running": scheduler.running if SCHEDULER_ENABLED else False,
            "rei_interval_minutes": REI_INTERVAL,
            "govcon_interval_minutes": GOVCON_INTERVAL
        }
    except Exception as e:
        results["integrations"]["scheduler"] = f"error: {e}"

    return results


@app.get("/rei")
async def rei() -> Any:
    """
    REI Dispo Engine entrypoint.
    """
    from src.engines.rei_engine import run_rei_engine
    result = await run_rei_engine()
    if isinstance(result, dict):
        return JSONResponse(result)
    return result


@app.get("/govcon")
async def govcon() -> Any:
    """
    GovCon Sub-Trap Engine entrypoint.
    """
    from src.engines.govcon_engine import run_govcon_engine
    result = await run_govcon_engine()
    if isinstance(result, dict):
        return JSONResponse(result)
    return result
```

---

## ENV VARS TO ADD (Railway)
```
SCHEDULER_ENABLED=true
REI_INTERVAL_MINUTES=15
GOVCON_INTERVAL_MINUTES=30
TWILIO_FROM_NUMBER=+1XXXXXXXXXX
```

---

## OPTION B: External Cron (Alternative)

If you prefer external scheduling, use cron-job.org (free) or n8n:

| Job | URL | Interval |
|-----|-----|----------|
| REI | `GET https://krizzyopslaunch-production.up.railway.app/rei` | Every 15 min |
| GovCon | `GET https://krizzyopslaunch-production.up.railway.app/govcon` | Every 30 min |

---

## VERIFY (After Deploy)
```
GET /health/deep
