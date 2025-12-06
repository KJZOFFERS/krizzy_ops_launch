from fastapi import FastAPI
import threading

from utils.validate_env import validate_env

# Validate environment variables before importing modules that access them
validate_env()

from engines.rei_engine import run_rei_engine, rei_lock
from engines.govcon_engine import run_govcon_engine, govcon_lock
from engines.watchdog_engine import run_watchdog_loop
from engines.outbound_engine import run_outbound_engine, outbound_lock, get_outbound_status
from engines.ingest_engine import run_ingest_cycle
from utils.kpi import kpi_push

app = FastAPI()

# Track daemon thread status
_daemon_threads_started = False

def _start_daemon_threads():
    """Start all daemon threads once."""
    global _daemon_threads_started
    if not _daemon_threads_started:
        threading.Thread(target=run_rei_engine, daemon=True).start()
        threading.Thread(target=run_govcon_engine, daemon=True).start()
        threading.Thread(target=run_watchdog_loop, daemon=True).start()
        threading.Thread(target=run_outbound_engine, daemon=True).start()
        _daemon_threads_started = True

# Uncomment to auto-start daemons on app startup
# _start_daemon_threads()

@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "daemons_started": _daemon_threads_started
    }

@app.post("/trigger/rei")
def trigger_rei():
    """Trigger REI processing engine."""
    if rei_lock.locked():
        return {"status": "running"}
    threading.Thread(target=run_rei_engine).start()
    return {"status": "started"}

@app.post("/trigger/govcon")
def trigger_govcon():
    """Trigger GovCon processing engine."""
    if govcon_lock.locked():
        return {"status": "running"}
    threading.Thread(target=run_govcon_engine).start()
    return {"status": "started"}

@app.post("/trigger/outbound")
def trigger_outbound():
    """Trigger outbound SMS engine."""
    if outbound_lock.locked():
        return {"status": "running"}
    threading.Thread(target=run_outbound_engine).start()
    return {"status": "started"}

@app.post("/trigger/ingest")
def trigger_ingest():
    """
    Run a single ingestion cycle for REI and GovCon.
    Reads NEW records from staging tables and upserts to production tables.
    """
    result = run_ingest_cycle()
    return result

@app.get("/outbound/status")
def outbound_status():
    """Get current outbound engine status."""
    return get_outbound_status()

@app.post("/kpi/push")
def kpi():
    """Push KPI metrics."""
    return kpi_push()
