from fastapi import FastAPI
import threading

from utils.validate_env import validate_env

# Validate environment variables before importing modules that access them
validate_env()

from engines.rei_engine import run_rei_engine, rei_lock
from engines.govcon_engine import run_govcon_engine, govcon_lock
from engines.watchdog_engine import run_watchdog_loop
from utils.kpi import kpi_push

app = FastAPI()

# Uncomment after Airtable schema is stable
# threading.Thread(target=run_rei_engine, daemon=True).start()
# threading.Thread(target=run_govcon_engine, daemon=True).start()
# threading.Thread(target=run_watchdog_loop, daemon=True).start()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/trigger/rei")
def trigger_rei():
    if rei_lock.locked():
        return {"status": "running"}
    threading.Thread(target=run_rei_engine).start()
    return {"status": "started"}

@app.post("/trigger/govcon")
def trigger_govcon():
    if govcon_lock.locked():
        return {"status": "running"}
    threading.Thread(target=run_govcon_engine).start()
    return {"status": "started"}

@app.post("/kpi/push")
def kpi():
    return kpi_push()
