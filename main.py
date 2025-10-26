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

async def engine_supervisor():
    """Start loops after app is up; keep them isolated so /health stays green."""
    await send_discord("ops", "KRIZZY OPS online. Spinning engines.")
    while True:
        try:
            # Run loops concurrently; each loop must handle its own retries.
            await asyncio.gather(
                run_rei_dispo(),
                run_govcon_subtrap(),
                start_watchdog()
            )
        except Exception as e:
            try:
                await send_discord("errors", f"Engine crash: {e!r}")
            except Exception:
                pass
            await asyncio.sleep(30)  # brief backoff before restart
        await asyncio.sleep(5)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(engine_supervisor())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
