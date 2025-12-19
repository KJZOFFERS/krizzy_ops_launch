import os
import time
from fastapi import FastAPI, HTTPException, Query
import threading
from sqlalchemy.exc import OperationalError

# Import DB infrastructure
from app_v2.database import engine, Base
import app_v2.models

app = FastAPI()

# Router wiring
from app_v2.llm_control.command_bus import router as command_bus_router

app.include_router(command_bus_router)


@app.get("/")
def root():
    """Default landing endpoint for uptime and platform probes."""
    return {
        "message": "Krizzy Ops Launch API",
        "health_endpoint": "/health",
        "docs": "/docs",
    }


@app.get("/favicon.ico")
def favicon():
    """Return an empty response for browsers requesting a favicon."""
    return {"status": "ok"}


def require_init_key(key: str | None):
    """Validate the INIT_KEY for protected admin endpoints."""
    expected = os.getenv("INIT_KEY")
    if not expected or key != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

DAEMONS_STARTED = False


@app.on_event("startup")
def startup_event():
    """
    Boot-time execution kernel.
    Starts autonomous worker loop if enabled.
    NOTE: DB tables are NOT created here - use /admin/init endpoint instead.
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


@app.post("/admin/init")
def admin_init(key: str | None = Query(default=None)):
    """
    Initialize database tables on demand.
    Protected by INIT_KEY environment variable.
    Retries up to 5 times with exponential backoff for sleeping Postgres.
    """
    require_init_key(key)

    # Retry because Railway Postgres may still be waking up
    last_err = None
    for attempt in range(1, 6):
        try:
            Base.metadata.create_all(bind=engine)
            return {"status": "ok", "attempt": attempt}
        except OperationalError as e:
            last_err = str(e)
            time.sleep(2 * attempt)

    raise HTTPException(status_code=503, detail=f"DB init failed after retries: {last_err}")
