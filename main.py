import asyncio
from fastapi import FastAPI
from engines.rei_dispo_engine import run_rei_dispo
from engines.govcon_subtrap_engine import run_govcon_subtrap
from utils.watchdog import start_watchdog
from utils.discord_utils import send_discord
import time

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "running", "ts": int(time.time())}

async def start_loops():
    """Run all loops continuously with async recovery."""
    while True:
        try:
            await asyncio.gather(
                run_rei_dispo(),
                run_govcon_subtrap(),
                start_watchdog()
            )
        except Exception as e:
            await send_discord("errors", f"⚠️ Engine crash: {e}")
        await asyncio.sleep(900)  # restart all engines every 15 min

@app.on_event("startup")
async def startup_event():
    await send_discord("ops", "🚀 KRIZZY OPS engines online.")
    asyncio.create_task(start_loops())
