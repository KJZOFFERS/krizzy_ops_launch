from fastapi import FastAPI
import asyncio, os, time

# Local imports
from engines.rei_dispo_engine import run_rei_dispo
from engines.govcon_subtrap_engine import run_govcon_subtrap
from utils.watchdog import start_watchdog
from utils.discord_utils import send_discord

app = FastAPI()

@app.get("/health")
async def health():
    """Used by Railway for container health check."""
    return {"status": "running", "timestamp": int(time.time())}

async def start_engines():
    """Run all KRIZZY OPS engines continuously."""
    while True:
        try:
            await asyncio.gather(
                run_rei_dispo(),
                run_govcon_subtrap(),
                start_watchdog()
            )
        except Exception as e:
            await send_discord("errors", f"⚠️ Engine failure: {e}")
        await asyncio.sleep(900)  # restart all loops every 15 min

@app.on_event("startup")
async def startup_event():
    await send_discord("ops", "🚀 KRIZZY OPS engines active.")
    asyncio.create_task(start_engines())

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
