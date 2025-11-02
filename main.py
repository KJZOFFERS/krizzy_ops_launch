import os
import asyncio
from fastapi import FastAPI
import aiohttp
import requests

# --- env ---
RUN_LOOPS = os.getenv("RUN_LOOPS_IN_WEB", "0") == "1"
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS")
KPI_TABLE = "KPI_Log"
LEADS_TABLE = "Leads_REI"
BUYERS_TABLE = "Buyers"
GOVCON_TABLE = "GovCon_Opportunities"

# --- web app ---
app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/healthz")
def healthz():
    return {"status": "healthy", "loops_in_web": RUN_LOOPS}

# --- helpers ---
def notify(msg: str):
    if WEBHOOK_OPS:
        try:
            requests.post(WEBHOOK_OPS, json={"content": msg}, timeout=8)
        except Exception:
            pass

async def airtable_create(table: str, fields: dict):
    if not (AIRTABLE_API_KEY and AIRTABLE_BASE_ID):
        return
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}",
               "Content-Type": "application/json"}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as s:
        await s.post(url, headers=headers, json={"fields": fields})

# --- one-shot cycles (idempotent placeholders; keep worker as the real engine) ---
async def rei_cycle():
    await airtable_create(KPI_TABLE, {"cycle": "rei", "source": "main"})
    notify("[REI] one-shot cycle complete (main)")
    return {"cycle": "rei", "status": "ok"}

async def govcon_cycle():
    await airtable_create(KPI_TABLE, {"cycle": "govcon", "source": "main"})
    notify("[GOVCON] one-shot cycle complete (main)")
    return {"cycle": "govcon", "status": "ok"}

@app.post("/run/rei")
async def run_rei():
    return await rei_cycle()

@app.post("/run/govcon")
async def run_govcon():
    return await govcon_cycle()

# --- optional background loops (guarded by env so you don't double-run with worker) ---
async def backend_loops():
    while True:
        await rei_cycle()
        await govcon_cycle()
        await asyncio.sleep(300)

@app.on_event("startup")
async def on_startup():
    if RUN_LOOPS:
        asyncio.create_task(backend_loops())
