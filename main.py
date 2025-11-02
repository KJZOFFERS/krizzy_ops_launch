import os
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from utils.discord_utils import post_ops, post_error
from utils.airtable_utils import safe_airtable_note
from utils.n8n_utils import trigger_rei, trigger_govcon, n8n_ready
from utils.watchdog import watchdog_loop

APP_NAME = "krizzy_ops_web"
VERSION = "2025-11-02T18:30:00Z"

STATE: Dict[str, Optional[str]] = {
    "rei_last_run": None,
    "govcon_last_run": None,
    "watchdog_last_ping": None,
    "version": VERSION,
}

WATCHDOG_ENABLED = os.getenv("WATCHDOG_ENABLED", "true").lower() == "true"
WATCHDOG_INTERVAL = int(os.getenv("WATCHDOG_INTERVAL", "60"))  # seconds
WATCHDOG_POST = os.getenv("WATCHDOG_POST_TO_DISCORD", "false").lower() == "true"

AIRTABLABLE = os.getenv("AIRTABLE_API_KEY") and os.getenv("AIRTABLE_BASE_ID")

app = FastAPI(title=APP_NAME)

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@app.on_event("startup")
async def on_startup():
    # Boot signal
    post_ops(f"🚀 {APP_NAME} v{VERSION} starting on Railway. WATCHDOG={WATCHDOG_ENABLED}")

    # Optional: log to Airtable (non-fatal if missing)
    safe_airtable_note(
        table=os.getenv("AIRTABLE_KPI_TABLE", "KPI_Log"),
        note=f"{APP_NAME} boot v{VERSION}",
        extra={"service": APP_NAME, "version": VERSION},
    )

    # Start watchdog loop (non-blocking)
    if WATCHDOG_ENABLED:
        asyncio.create_task(
            watchdog_loop(
                interval=WATCHDOG_INTERVAL,
                on_ping=lambda: _on_watchdog_ping()
            )
        )

def _on_watchdog_ping():
    STATE["watchdog_last_ping"] = _utc_now()
    if WATCHDOG_POST:
        post_ops(f"🟢 WATCHDOG OK — {STATE['watchdog_last_ping']}")
    # Try to write a lightweight KPI heartbeat if configured
    safe_airtable_note(
        table=os.getenv("AIRTABLE_KPI_TABLE", "KPI_Log"),
        note="watchdog_heartbeat",
        extra={"service": APP_NAME, "t": STATE["watchdog_last_ping"]},
    )

@app.get("/")
def root():
    return {"status": "ok", "service": APP_NAME, "version": VERSION}

@app.get("/health")
def health():
    required_env = ["DISCORD_WEBHOOK_OPS", "DISCORD_WEBHOOK_ERRORS"]
    # Only mark n8n section ready if URLs are provided (no guessing)
    n8n_section = {
        "rei_url_set": bool(os.getenv("N8N_REI_URL")),
        "govcon_url_set": bool(os.getenv("N8N_GOVCON_URL")),
        "api_key_set": bool(os.getenv("N8N_API_KEY")),
    }
    return JSONResponse(
        {
            "status": "healthy",
            "service": APP_NAME,
            "version": VERSION,
            "env": {
                "airtable_ready": bool(AIRTABLABLE),
                "discord_ready": all(os.getenv(k) for k in required_env),
                "n8n_ready": n8n_ready(),
            },
            "n8n": n8n_section,
            "state": STATE,
        }
    )

@app.get("/healthz")
def healthz():
    # Legacy path
    return {"status": "healthy", "service": APP_NAME}

@app.get("/status")
def status():
    return STATE

@app.post("/run/rei")
async def run_rei(payload: Dict[str, Any] = {}):
    if not os.getenv("N8N_REI_URL"):
        raise HTTPException(status_code=400, detail="N8N_REI_URL not set")
    try:
        resp = await trigger_rei(payload)
        STATE["rei_last_run"] = _utc_now()
        post_ops(f"✅ REI_DISPO_ENGINE triggered")
        safe_airtable_note(
            table=os.getenv("AIRTABLE_KPI_TABLE", "KPI_Log"),
            note="rei_trigger",
            extra={"payload_keys": list(payload.keys()) if payload else []},
        )
        return {"ok": True, "n8n": resp, "ts": STATE["rei_last_run"]}
    except Exception as e:
        post_error(f"❌ REI trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run/govcon")
async def run_govcon(payload: Dict[str, Any] = {}):
    if not os.getenv("N8N_GOVCON_URL"):
        raise HTTPException(status_code=400, detail="N8N_GOVCON_URL not set")
    try:
        resp = await trigger_govcon(payload)
        STATE["govcon_last_run"] = _utc_now()
        post_ops(f"✅ GOVCON_SUBTRAP_ENGINE triggered")
        safe_airtable_note(
            table=os.getenv("AIRTABLE_KPI_TABLE", "KPI_Log"),
            note="govcon_trigger",
            extra={"payload_keys": list(payload.keys()) if payload else []},
        )
        return {"ok": True, "n8n": resp, "ts": STATE["govcon_last_run"]}
    except Exception as e:
        post_error(f"❌ GOVCON trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
