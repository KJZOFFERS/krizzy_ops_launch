import os, asyncio, time
from datetime import datetime, timezone
from typing import Dict, Any

import httpx
from fastapi import FastAPI, BackgroundTasks

APP_NAME = "krizzy_ops_web"

# ---- Env helpers ----
def env(name: str, default: str = "") -> str:
    v = os.getenv(name, default)
    return v.strip() if v else ""

AIRTABLE_API_KEY   = env("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID   = env("AIRTABLE_BASE_ID")
KPI_TABLE          = env("KPI_TABLE", "KPI_Log")

DISCORD_OPS        = env("DISCORD_WEBHOOK_OPS")
DISCORD_ERRORS     = env("DISCORD_WEBHOOK_ERRORS")

RUN_REI            = env("RUN_REI", "1") == "1"
RUN_GOVCON         = env("RUN_GOVCON", "1") == "1"

REI_INTERVAL_SEC   = int(env("REI_INTERVAL_MINUTES", "15")) * 60
GOV_INTERVAL_SEC   = int(env("GOVCON_INTERVAL_MINUTES", "20")) * 60
WATCHDOG_INTERVAL  = int(env("WATCHDOG_INTERVAL_SECONDS", "60"))

# ---- App + in-memory state ----
app = FastAPI()
state: Dict[str, Any] = {
    "boot_ts": time.time(),
    "rei_last_run": None,
    "govcon_last_run": None,
    "watchdog_last_ping": None,
    "loops": {"rei": RUN_REI, "govcon": RUN_GOVCON}
}

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---- IO helpers ----
async def post_discord(webhook: str, content: str) -> None:
    if not webhook:
        return
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(webhook, json={"content": content})
        except Exception:
            # Best-effort; don't crash loops on Discord hiccups
            pass

async def airtable_insert(table: str, fields: Dict[str, Any]) -> None:
    if not (AIRTABLE_API_KEY and AIRTABLE_BASE_ID and table):
        return
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    payload = {"records": [{"fields": fields}]}
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            await client.post(url, headers=headers, json=payload)
        except Exception:
            # Quiet fail; keep loops resilient
            pass

# ---- Business loop stubs (hook in your engines here) ----
async def run_rei_dispo_once() -> Dict[str, Any]:
    """
    Hook point: call your REI dispo engine here (scrape/enrich/match).
    This baseline logs a heartbeat to Airtable + Discord.
    """
    ts = utcnow_iso()
    fields = {"Engine": "REI_DISPO", "Status": "ran", "Timestamp": ts}
    await airtable_insert(KPI_TABLE, fields)
    await post_discord(DISCORD_OPS, f"✅ REI_DISPO ran @ {ts}")
    return {"ok": True, "ts": ts}

async def run_govcon_once() -> Dict[str, Any]:
    """
    Hook point: call your GovCon Sub-Trap here (SAM/FPDS ingest, filter, push).
    Baseline logs a heartbeat to Airtable + Discord.
    """
    ts = utcnow_iso()
    fields = {"Engine": "GOVCON_SUBTRAP", "Status": "ran", "Timestamp": ts}
    await airtable_insert(KPI_TABLE, fields)
    await post_discord(DISCORD_OPS, f"✅ GOVCON_SUBTRAP ran @ {ts}")
    return {"ok": True, "ts": ts}

# ---- Background loops ----
async def watchdog_loop():
    while True:
        ts = utcnow_iso()
        state["watchdog_last_ping"] = ts
        await airtable_insert(KPI_TABLE, {"Engine": "WATCHDOG", "Status": "ping", "Timestamp": ts})
        await asyncio.sleep(WATCHDOG_INTERVAL)

async def rei_loop():
    while True:
        try:
            result = await run_rei_dispo_once()
            state["rei_last_run"] = result.get("ts")
        except Exception as e:
            await post_discord(DISCORD_ERRORS, f"❌ REI_DISPO error: {e}")
        await asyncio.sleep(REI_INTERVAL_SEC)

async def govcon_loop():
    while True:
        try:
            result = await run_govcon_once()
            state["govcon_last_run"] = result.get("ts")
        except Exception as e:
            await post_discord(DISCORD_ERRORS, f"❌ GOVCON_SUBTRAP error: {e}")
        await asyncio.sleep(GOV_INTERVAL_SEC)

@app.on_event("startup")
async def startup_tasks():
    # Kick off background tasks
    asyncio.create_task(watchdog_loop())
    if RUN_REI:
        asyncio.create_task(rei_loop())
    if RUN_GOVCON:
        asyncio.create_task(govcon_loop())
    await post_discord(DISCORD_OPS, f"🚀 {APP_NAME} started @ {utcnow_iso()} (loops: {state['loops']})")

# ---- Routes ----
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": APP_NAME,
        "uptime_sec": round(time.time() - state["boot_ts"], 1),
        "loops": state["loops"],
        "rei_last_run": state["rei_last_run"],
        "govcon_last_run": state["govcon_last_run"],
        "watchdog_last_ping": state["watchdog_last_ping"],
    }

@app.get("/health")
def health():
    env_ok = bool(AIRTABLE_API_KEY and AIRTABLE_BASE_ID)
    return {
        "status": "healthy",
        "service": APP_NAME,
        "env": {
            "airtable": env_ok,
            "discord_ops": bool(DISCORD_OPS),
            "discord_errors": bool(DISCORD_ERRORS),
        }
    }

@app.get("/healthz")
def healthz():
    return {"status": "healthy", "service": APP_NAME}

@app.post("/run/rei")
async def run_rei(background: BackgroundTasks):
    background.add_task(run_rei_dispo_once)
    return {"queued": True, "engine": "REI_DISPO"}

@app.post("/run/govcon")
async def run_govcon(background: BackgroundTasks):
    background.add_task(run_govcon_once)
    return {"queued": True, "engine": "GOVCON_SUBTRAP"}
