from fastapi import FastAPI, HTTPException
import threading

from app_v2.agent.v2_llm_worker import run_worker_loop
from database import engine, Base
import app_v2.models

app = FastAPI()

DAEMONS_STARTED = False


@app.on_event("startup")
def startup_event():
    """
    Boot-time execution kernel.
    Creates DB tables and starts autonomous worker loop.
    """
    global DAEMONS_STARTED

    # Create all tables
    Base.metadata.create_all(bind=engine)

    try:
        # Start autonomous execution loop
        worker_thread = threading.Thread(target=run_worker_loop, daemon=True)
        worker_thread.start()

        DAEMONS_STARTED = True

    except Exception as e:
        DAEMONS_STARTED = False
        raise RuntimeError(f"Failed to start worker: {e}")


@app.get("/health")
def health():
    """Health check endpoint."""
    if not DAEMONS_STARTED:
        raise HTTPException(
            status_code=500,
            detail="Execution kernel not running"
        )

    return {
        "status": "ok",
        "daemons_started": True
    }
