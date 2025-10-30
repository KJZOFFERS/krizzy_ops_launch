from fastapi import FastAPI
import threading
import time
import uvicorn

from engines.rei_dispo_engine import loop_rei, last_rei_run
from engines.govcon_subtrap_engine import loop_govcon, last_govcon_run
from utils.watchdog import loop_watchdog, last_watchdog_ping

app = FastAPI()
service_start_time = int(time.time())

@app.get("/health")
async def health():
    return {"status": "running", "service_start_time": service_start_time}

@app.get("/diagnostics")
async def diagnostics():
    return {
        "rei_last_run": last_rei_run,
        "govcon_last_run": last_govcon_run,
        "watchdog_last_ping": last_watchdog_ping
    }

def start_rei_loop():
    while True:
        try: loop_rei()
        except Exception as e: print(f"[REI_LOOP_ERROR] {e}")
        time.sleep(60)

def start_govcon_loop():
    while True:
        try: loop_govcon()
        except Exception as e: print(f"[GOVCON_LOOP_ERROR] {e}")
        time.sleep(300)

def start_watchdog_loop():
    while True:
        try: loop_watchdog()
        except Exception as e: print(f"[WATCHDOG_LOOP_ERROR] {e}")
        time.sleep(30)

@app.on_event("startup")
def start_loops():
    threading.Thread(target=start_rei_loop, daemon=True).start()
    threading.Thread(target=start_govcon_loop, daemon=True).start()
    threading.Thread(target=start_watchdog_loop, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
