from fastapi import FastAPI
import asyncio, os, time
from engines.rei_dispo_engine import run_rei_dispo
from engines.govcon_subtrap_engine import run_govcon_subtrap
from utils.watchdog import start_watchdog
from utils.discord_utils import send_discord

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "running", "ts": int(time.time())}

async def start_engines():
    """Run all KRIZZY OPS engines continuously."""
    await send_discord("ops", "KRIZZY OPS online. Engines spinning up.")
    while True:
        try:
            await asyncio.gather(
                run_rei_dispo(),
                run_govcon_subtrap(),
                start_watchdog()
            )
        except Exception as e:
            await send_discord("errors", f"⚠️ Engine crash: {e!r}")
            await asyncio.sleep(30)
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_engines())

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
