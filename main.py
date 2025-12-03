import threading
import asyncio
import time
from fastapi import FastAPI
from src.app import app

# Engines
from src.engines.rei_engine import run_rei_engine
from src.engines.govcon_engine import run_govcon_engine

# Watchdog & logging
from src.common.discord_notify import notify_error, notify_ops


# ============================================================
# THREAD LOCKS (prevents double-runs and race conditions)
# ============================================================
rei_lock = threading.Lock()
govcon_lock = threading.Lock()


# ============================================================
# WATCHDOG PROTECTION
# ============================================================
def watchdog_loop():
    while True:
        try:
            notify_ops("Watchdog: System running normally.")
        except Exception as e:
            notify_error(f"Watchdog error: {e}")
        time.sleep(30)  # Check every 30 seconds


# ============================================================
# ENGINE LOOP WRAPPERS
# ============================================================
def rei_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            with rei_lock:
                loop.run_until_complete(run_rei_engine())
        except Exception as e:
            notify_error(f"REI Loop Crash: {e}")
        time.sleep(60)  # 1 minute


def govcon_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            with govcon_lock:
                loop.run_until_complete(run_govcon_engine())
        except Exception as e:
            notify_error(f"GovCon Loop Crash: {e}")
        time.sleep(300)  # 5 minutes


# ============================================================
# FASTAPI ON_STARTUP — SPAWNS THREADS
# ============================================================
@app.on_event("startup")
def start_background_engines():
    notify_ops("🔥 KRIZZY OPS Launching Thread Engines…")

    threading.Thread(target=rei_loop, daemon=True).start()
    threading.Thread(target=govcon_loop, daemon=True).start()
    threading.Thread(target=watchdog_loop, daemon=True).start()

    notify_ops("🔥 KRIZZY OPS Engines Running 24/7")


# ============================================================
# MANUAL TRIGGER ROUTES
# ============================================================
@app.get("/run/rei")
async def run_rei_manual():
    with rei_lock:
        return await run_rei_engine()


@app.get("/run/govcon")
async def run_govcon_manual():
    with govcon_lock:
        return await run_govcon_engine()


@app.get("/health")
async def health():
    return {"status": "OK", "engine": "KRIZZY_OPS", "mode": "thread+watchdog"}
watchdog"}

