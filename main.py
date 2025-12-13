from fastapi import FastAPI, HTTPException
import threading

from app_v2.agent.v2_llm_worker import run_worker_loop

# V2 database and models
from database import engine, Base
import app_v2.models  # Force model registration
from app_v2.scheduler import scheduler_loop

app = FastAPI()

DAEMONS_STARTED = False


@app.on_event("startup")
def startup_event():
    """
    Boot-time execution kernel.
    Creates tables and starts scheduler + worker.
    """
    global DAEMONS_STARTED

    # Create all tables (including ledger and jobs)
    Base.metadata.create_all(bind=engine)

    try:
        # Start scheduler and worker loops
        threading.Thread(target=scheduler_loop, daemon=True).start()
        threading.Thread(target=run_worker_loop, daemon=True).start()

        DAEMONS_STARTED = True

    except Exception as e:
        DAEMONS_STARTED = False
        raise RuntimeError(f"Failed to start worker: {e}")


@app.get("/health")
def health():
    """
    Health MUST reflect execution truth.
    """
    if not DAEMONS_STARTED:
        raise HTTPException(
            status_code=500,
            detail="Execution kernel not running"
        )

    return {
        "status": "ok",
        "daemons_started": True
    }
