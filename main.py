import logging
import os
import time

from fastapi import FastAPI, HTTPException, Query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("krizzy_ops_launch.main")

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


@app.on_event("startup")
def startup_event():
    """Minimal startup: register routers and log readiness."""
    logger.info("Application startup complete; routers registered.")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "service ready"
    }


@app.post("/admin/init")
def admin_init(key: str | None = Query(default=None)):
    """
    Initialize database tables on demand.
    Protected by INIT_KEY environment variable.
    Retries up to 5 times with exponential backoff for sleeping Postgres.
    """
    require_init_key(key)

    # Lazy import to avoid any DB work before explicit initialization
    from app_v2.database import engine, Base
    import app_v2.models  # noqa: F401  # ensure models are registered

    logger.info("/admin/init invoked; starting schema creation")

    # Retry because Railway Postgres may still be waking up
    last_err = None
    for attempt in range(1, 6):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema ensured on attempt %s", attempt)
            return {"status": "ok", "attempt": attempt}
        except Exception as e:
            last_err = str(e)
            logger.warning(
                "Database init attempt %s failed: %s", attempt, last_err
            )
            time.sleep(2 * attempt)

    raise HTTPException(status_code=503, detail=f"DB init failed after retries: {last_err}")
