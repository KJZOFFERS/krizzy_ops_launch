import os
from fastapi import FastAPI, HTTPException
import threading

app = FastAPI()

DAEMONS_STARTED = False


@app.on_event("startup")
def startup_event():
    """
    Boot-time execution kernel.
    Starts autonomous worker loop. DB-free startup.
    """
    global DAEMONS_STARTED

    # Only start worker if enabled
    worker_enabled = os.getenv("WORKER_ENABLED", "true").lower() == "true"

    if worker_enabled:
        try:
            # Lazy import to avoid eager DB connection
            from app_v2.agent.v2_llm_worker import run_worker_loop

            # Start autonomous execution loop
            worker_thread = threading.Thread(target=run_worker_loop, daemon=True)
            worker_thread.start()

            DAEMONS_STARTED = True

        except Exception as e:
            DAEMONS_STARTED = False
            raise RuntimeError(f"Failed to start worker: {e}")
    else:
        DAEMONS_STARTED = False


@app.get("/health")
def health():
    """Health check endpoint."""
    worker_enabled = os.getenv("WORKER_ENABLED", "true").lower() == "true"

    if worker_enabled and not DAEMONS_STARTED:
        raise HTTPException(
            status_code=500,
            detail="Execution kernel not running"
        )

    return {
        "status": "ok",
        "daemons_started": DAEMONS_STARTED,
        "worker_enabled": worker_enabled
    }
