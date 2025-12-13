<<<<<<< Updated upstream
=======
from fastapi import FastAPI, HTTPException
>>>>>>> Stashed changes
import threading
from fastapi import FastAPI, HTTPException

from app_v2.agent.v2_llm_worker import run_worker_loop

# V2 database and models
from database import engine, Base
import app_v2.models  # Force model registration
from app_v2.scheduler import scheduler_loop
from app_v2.agent.v2_llm_worker import run_worker_loop

app = FastAPI()

DAEMONS_STARTED = False

<<<<<<< Updated upstream
=======

@app.on_event("startup")
def startup_event():
    """Create tables and start V2 scheduler + worker"""
    global _daemon_threads_started

    # Create all tables (including ledger and jobs)
    Base.metadata.create_all(bind=engine)

    # Start scheduler and worker loops
    try:
        threading.Thread(target=scheduler_loop, daemon=True).start()
        threading.Thread(target=run_worker_loop, daemon=True).start()
        _daemon_threads_started = True
    except Exception as e:
        _daemon_threads_started = False
        raise RuntimeError(f"V2 execution failed to start: {e}")

def _start_daemon_threads():
    """Start all daemon threads once."""
    global _daemon_threads_started
    if not _daemon_threads_started:
        threading.Thread(target=run_rei_engine, daemon=True).start()
        threading.Thread(target=run_govcon_engine, daemon=True).start()
        threading.Thread(target=run_watchdog_loop, daemon=True).start()
        threading.Thread(target=run_outbound_engine, daemon=True).start()
        _daemon_threads_started = True
>>>>>>> Stashed changes

@app.on_event("startup")
def startup_event():
    """
    Boot-time execution kernel.
    If this does not start, the system is DEAD.
    """
    global DAEMONS_STARTED

    try:
        worker_thread = threading.Thread(
            target=run_worker_loop,
            daemon=True
        )
        worker_thread.start()

        DAEMONS_STARTED = True

    except Exception as e:
        DAEMONS_STARTED = False
        raise RuntimeError(f"Failed to start worker: {e}")


@app.get("/health")
def health():
<<<<<<< Updated upstream
    """
    Health MUST reflect execution truth.
    """
    if not DAEMONS_STARTED:
        raise HTTPException(
            status_code=500,
            detail="Execution kernel not running"
        )

=======
    """Health check endpoint."""
    if not _daemon_threads_started:
        raise HTTPException(status_code=500, detail="V2 execution kernel not running")
>>>>>>> Stashed changes
    return {
        "status": "ok",
        "daemons_started": True
    }
