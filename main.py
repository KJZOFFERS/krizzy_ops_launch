import logging
import os
import threading
import time
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException

from sqlalchemy.exc import OperationalError

from utils.airtable_meta import AirtableMetaCache
from utils.codex import Codex, CodexError
from utils.db import db_ping, get_engine
from utils.models import Base as OpsBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("krizzy.ops.launch")

app = FastAPI()

# Router wiring
from app_v2.llm_control.command_bus import router as command_bus_router
from app_v2.routes_feeds import router as feeds_router
from job_queue import enqueue_engine_run

app.include_router(command_bus_router)
app.include_router(feeds_router)


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

    logger.info("Boot sequence starting", extra={"worker_enabled": worker_enabled})

    if worker_enabled:
        try:
            # Lazy import to avoid eager DB connection
            from app_v2.agent.v2_llm_worker import run_worker_loop

            # Start autonomous execution loop
            worker_thread = threading.Thread(target=run_worker_loop, daemon=True)
            worker_thread.start()

            DAEMONS_STARTED = True

            logger.info("Worker loop started", extra={"thread_name": worker_thread.name})

        except Exception as e:
            DAEMONS_STARTED = False
            raise RuntimeError(f"Failed to start worker: {e}")
    else:
        DAEMONS_STARTED = False
        logger.info("Worker disabled via WORKER_ENABLED flag")


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
def admin_init(x_init_key: str = Header(default="")):
    """
    Initialize database tables on demand.
    Protected by INIT_KEY environment variable.
    Retries up to 5 times with exponential backoff for sleeping Postgres.
    """
    cx = Codex.load()
    if x_init_key != cx.INIT_KEY:
        raise HTTPException(status_code=401, detail="bad init key")

    # Lazy import to avoid touching DB until explicitly requested
    from app_v2.database import Base
    import app_v2.models  # noqa: F401  # Ensure all models are registered with metadata

    # Retry because Railway Postgres may still be waking up
    last_err = None
    for attempt in range(1, 6):
        try:
            engine = get_engine(cx.DATABASE_URL)
            Base.metadata.create_all(bind=engine)
            OpsBase.metadata.create_all(bind=engine)
            return {"status": "ok", "attempt": attempt}
        except OperationalError as e:
            last_err = str(e)
            time.sleep(2 * attempt)

    raise HTTPException(status_code=503, detail=f"DB init failed after retries: {last_err}")


@app.get("/codex/check")
def codex_check():
    try:
        cx = Codex.load()
    except CodexError as e:
        return {"ok": False, "error": str(e)}

    db = db_ping(cx.DATABASE_URL)
    if not db["ok"]:
        return {"ok": False, "error": "DB_PING_FAIL", "detail": db}

    # Airtable meta existence check (no table writes)
    meta = AirtableMetaCache(cx.AIRTABLE_PAT, cx.AIRTABLE_BASE_ID)
    data = meta.fetch()
    return {"ok": True, "tables": len(data.get("tables", []))}


@app.get("/ops/db")
def ops_db():
    """Operational endpoint to probe database connectivity."""
    from utils.db_probe import probe_db

    result = probe_db()
    if result.get("ok"):
        return result

    raise HTTPException(status_code=503, detail=result)


@app.post("/scheduler/tick")
def scheduler_tick():
    """Enqueue recurring engine jobs without executing inline."""
    jobs = []
    for engine in ["rei", "govcon", "deal_closer"]:
        job = enqueue_engine_run(engine)
        jobs.append({"id": job.id, "engine": engine})
    return {"status": "enqueued", "jobs": jobs}


@app.post("/trigger/rei")
def trigger_rei(payload: Dict[str, Any] | None = None):
    """Queue a single REI engine run."""
    job = enqueue_engine_run("rei", payload=payload)
    return {"status": "enqueued", "job_id": job.id}


@app.post("/trigger/govcon")
def trigger_govcon(payload: Dict[str, Any] | None = None):
    """Queue a single GovCon engine run."""
    job = enqueue_engine_run("govcon", payload=payload)
    return {"status": "enqueued", "job_id": job.id}


@app.post("/trigger/deal-closer")
def trigger_deal_closer(payload: Dict[str, Any] | None = None):
    """Queue a single Deal Closer engine run."""
    job = enqueue_engine_run("deal_closer", payload=payload)
    return {"status": "enqueued", "job_id": job.id}
