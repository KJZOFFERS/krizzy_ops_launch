import threading
from fastapi import FastAPI, HTTPException

from app_v2.agent.v2_llm_worker import run_worker_loop

app = FastAPI()

DAEMONS_STARTED = False


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
