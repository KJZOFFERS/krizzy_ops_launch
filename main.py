import threading
import asyncio
import time

from fastapi import FastAPI
from src.app import app  # FastAPI app

# Import engines
from src.engines.rei_engine import run_rei_engine
from src.engines.govcon_engine import run_govcon_engine


# ===============================
# Thread-safe engine wrappers
# ===============================
rei_lock = threading.Lock()
govcon_lock = threading.Lock()


def rei_loop():
    """Runs REI engine every 60 seconds."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            with rei_lock:
                loop.run_until_complete(run_rei_engine())
        except Exception as e:
            print(f"[REI LOOP ERROR] {e}")

        time.sleep(60)


def govcon_loop():
    """Runs GovCon engine every 300 seconds."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            with govcon_lock:
                loop.run_until_complete(run_govcon_engine())
        except Exception as e:
            print(f"[GOVCON LOOP ERROR] {e}")

        time.sleep(300)


# ===============================
# Start threads on startup
# ===============================
@app.on_event("startup")
def start_background_engines():
    rei_thread = threading.Thread(target=rei_loop, daemon=True)
    govcon_thread = threading.Thread(target=govcon_loop, daemon=True)

    rei_thread.start()
    govcon_thread.start()

    print("🔥 KRIZZY OPS Engines Started")


# ===============================
# Manual Trigger Endpoints
# ===============================
@app.get("/run/rei")
async def manual_rei():
    with rei_lock:
        return await run_rei_engine()


@app.get("/run/govcon")
async def manual_govcon():
    with govcon_lock:
        return await run_govcon_engine()


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "KRIZZY_OPS"}
