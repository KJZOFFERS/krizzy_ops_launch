from fastapi import FastAPI
import threading

from utils.validate_env import validate_env

# Validate environment variables before importing modules that access them
validate_env()

from engines.rei_engine import run_rei_engine, rei_lock
from engines.govcon_engine import run_govcon_engine, govcon_lock
from engines.watchdog_engine import run_watchdog_loop
from engines.outbound_engine import run_outbound_engine, outbound_lock, get_outbound_status
from utils.kpi import kpi_push

app = FastAPI()

# Uncomment after Airtable schema is stable
# threading.Thread(target=run_rei_engine, daemon=True).start()
# threading.Thread(target=run_govcon_engine, daemon=True).start()
# threading.Thread(target=run_watchdog_loop, daemon=True).start()
# threading.Thread(target=run_outbound_engine, daemon=True).start()

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

@app.post("/trigger/outbound")
def trigger_outbound():
    if outbound_lock.locked():
        return {"status": "running"}
    threading.Thread(target=run_outbound_engine).start()
    return {"status": "started"}

@app.post("/trigger/ingest")
def trigger_ingest():
    """Trigger both REI and GovCon ingestion engines"""
    rei_is_running = rei_lock.locked()
    govcon_is_running = govcon_lock.locked()
    
    if not rei_is_running:
        threading.Thread(target=run_rei_engine).start()
    
    if not govcon_is_running:
        threading.Thread(target=run_govcon_engine).start()
    
    # Determine overall status: "running" if both already running, "started" if any were started
    overall_status = "running" if (rei_is_running and govcon_is_running) else "started"
    
    return {
        "status": overall_status,
        "rei": "running" if rei_is_running else "started",
        "govcon": "running" if govcon_is_running else "started"
    }

@app.get("/outbound/status")
def outbound_status():
    return get_outbound_status()

@app.post("/kpi/push")
def kpi():
    return kpi_push()
