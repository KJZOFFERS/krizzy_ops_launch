import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from engines.rei_dispo_engine import loop_rei
from engines.govcon_subtrap_engine import loop_govcon
from utils.discord_utils import post_ops, post_error
from utils.airtable_utils import safe_airtable_note
from utils.watchdog import watchdog_loop

APP_NAME = "krizzy_ops_web"
VERSION = "2025-11-03T00:00:00Z"

REI_INTERVAL = int(os.getenv("REI_INTERVAL", "900"))          # 15m default
GOVCON_INTERVAL = int(os.getenv("GOVCON_INTERVAL", "1800"))   # 30m default
WATCHDOG_INTERVAL = int(os.getenv("WATCHDOG_INTERVAL", "60")) # 1m default
WATCHDOG_POST = os.getenv("WATCHDOG_POST", "1") == "1"

STATE = {
    "rei_last_run": None,
    "govcon_last_run": None,
    "watchdog_last_ping": None,
}

app = FastAPI(title=APP_NAME, version=VERSION)

@app.get("/health")
def health():
    return JSONResponse({"ok": True, "app": APP_NAME, "version": VERSION})

async def _main_loop():
    rei_acc = 0
    gov_acc = 0
    tick = 5  # seconds
    while True:
        try:
            rei_acc += tick
            gov_acc += tick

            if rei_acc >= REI_INTERVAL:
                loop_rei()
                STATE["rei_last_run"] = "ok"
                safe_airtable_note(table=os.getenv("AIRTABLE_KPI_TABLE", "KPI_Log"), note="rei_cycle")
                rei_acc = 0

            if gov_acc >= GOVCON_INTERVAL:
                loop_govcon()
                STATE["govcon_last_run"] = "ok"
                safe_airtable_note(table=os.getenv("AIRTABLE_KPI_TABLE", "KPI_Log"), note="govcon_cycle")
                gov_acc = 0

        except Exception as e:
            post_error(f"MAIN LOOP ERROR: {e}")

        await asyncio.sleep(tick)

def _on_watchdog_ping():
    STATE["watchdog_last_ping"] = "ok"
    if WATCHDOG_POST:
        post_ops("🟢 WATCHDOG OK")

@app.on_event("startup")
async def startup():
    post_ops(f"🚀 {APP_NAME} {VERSION} starting")
    asyncio.create_task(_main_loop())
    asyncio.create_task(watchdog_loop(interval=WATCHDOG_INTERVAL, on_ping=_on_watchdog_ping))

