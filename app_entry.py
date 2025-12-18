"""
KRIZZY OPS - Canonical FastAPI Entrypoint
==========================================
This is the ONE production entrypoint for Railway.

Start Command: uvicorn app_entry:app --host 0.0.0.0 --port $PORT

Boot-safe: NO DB calls at startup. Use POST /admin/init to initialize DB.
"""

import os
import time
import threading
from fastapi import FastAPI, HTTPException, Query
from sqlalchemy.exc import OperationalError

# =============================================================================
# App Configuration
# =============================================================================

app = FastAPI(
    title="KRIZZY OPS",
    version="2.0.0",
    description="Unified REI + GovCon Operations Platform"
)

# =============================================================================
# Lazy Imports & Boot-Safe Design
# =============================================================================
# All DB/Airtable imports are done INSIDE endpoint functions to avoid
# connection attempts at import time. This keeps the app boot-safe.


def _get_db_engine():
    """Lazy import of DB engine."""
    from app_v2.database import engine
    return engine


def _get_db_base():
    """Lazy import of DB Base."""
    from app_v2.database import Base
    import app_v2.models  # noqa: F401 - registers models
    return Base


# =============================================================================
# Auth Helper
# =============================================================================

def require_init_key(key: str | None):
    """Validate the INIT_KEY for protected admin endpoints."""
    expected = os.getenv("INIT_KEY")
    if not expected or key != expected:
        raise HTTPException(status_code=403, detail="Forbidden")


# =============================================================================
# Mount Routers
# =============================================================================

# LLM Control Router (V2)
from app_v2.llm_control.command_bus import router as llm_router
app.include_router(llm_router, prefix="/v2/llm", tags=["llm_control"])


# =============================================================================
# Daemon State
# =============================================================================

DAEMONS_STARTED = False


# =============================================================================
# Startup Event (Boot-Safe)
# =============================================================================

@app.on_event("startup")
def startup_event():
    """
    Boot-time initialization.

    - NO DB calls here (boot-safe)
    - Daemons only start if AUTOPILOT_ENABLED=1
    """
    global DAEMONS_STARTED

    autopilot_enabled = os.getenv("AUTOPILOT_ENABLED", "0") == "1"

    if autopilot_enabled:
        try:
            # Lazy import to avoid eager DB connection
            from app_v2.agent.v2_llm_worker import run_worker_loop

            worker_thread = threading.Thread(target=run_worker_loop, daemon=True)
            worker_thread.start()
            DAEMONS_STARTED = True

        except Exception as e:
            DAEMONS_STARTED = False
            # Don't crash startup - just log
            print(f"[WARN] Worker failed to start: {e}")
    else:
        DAEMONS_STARTED = False


# =============================================================================
# Health & Admin Endpoints
# =============================================================================

@app.get("/health", tags=["admin"])
def health():
    """
    Health check endpoint.
    No DB or Airtable calls - always responds.
    """
    return {
        "status": "ok",
        "version": "2.0.0",
        "daemons_started": DAEMONS_STARTED,
        "autopilot_enabled": os.getenv("AUTOPILOT_ENABLED", "0") == "1"
    }


@app.post("/admin/init", tags=["admin"])
def admin_init(key: str | None = Query(default=None)):
    """
    Initialize database tables on demand.
    Protected by INIT_KEY. Retries up to 5 times for sleeping Postgres.
    """
    require_init_key(key)

    engine = _get_db_engine()
    Base = _get_db_base()

    last_err = None
    for attempt in range(1, 6):
        try:
            Base.metadata.create_all(bind=engine)
            return {"status": "ok", "attempt": attempt}
        except OperationalError as e:
            last_err = str(e)
            time.sleep(2 * attempt)

    raise HTTPException(status_code=503, detail=f"DB init failed after retries: {last_err}")


@app.get("/admin/routes", tags=["admin"])
def admin_routes(key: str | None = Query(default=None)):
    """
    List all registered routes (for verification).
    Protected by INIT_KEY.
    """
    require_init_key(key)

    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods - {"HEAD", "OPTIONS"}),
                "name": route.name
            })
    return {"routes": sorted(routes, key=lambda r: r["path"])}


# =============================================================================
# Metrics Endpoint
# =============================================================================

@app.get("/metrics", tags=["monitoring"])
def metrics():
    """System metrics from V2 state machine."""
    from app_v2.models.system_state import system_state
    return system_state.get_status()


# =============================================================================
# V2 Engine Triggers (app_v2)
# =============================================================================

@app.post("/trigger/input", tags=["engines_v2"])
def trigger_input():
    """Manual trigger for V2 input engine (one cycle)."""
    from app_v2.engines.input_engine import InputEngine
    engine_instance = InputEngine()
    result = engine_instance.run_input_cycle()
    return {"status": "ok", **result}


@app.post("/trigger/underwriting", tags=["engines_v2"])
def trigger_underwriting():
    """Manual trigger for V2 underwriting engine (one cycle)."""
    from app_v2.engines.underwriting_engine import run_underwriting_cycle
    result = run_underwriting_cycle()
    return {"status": "ok", **result}


# =============================================================================
# Legacy Engine Triggers (engines/)
# =============================================================================

@app.post("/trigger/ingest", tags=["engines_legacy"])
def trigger_ingest():
    """
    Manual trigger for ingest engine.
    Processes Inbound_REI_Raw and Inbound_GovCon_Raw into production tables.
    """
    from engines.ingest_engine import run_ingest_cycle
    result = run_ingest_cycle()
    return {"status": "ok", **result}


@app.post("/trigger/rei", tags=["engines_legacy"])
def trigger_rei():
    """
    Manual trigger for REI scoring engine (single pass, non-blocking).
    Scores leads in Leads_REI table.
    """
    from engines.rei_engine import run_rei_engine, rei_lock
    import threading

    # Run single pass in background thread (non-blocking)
    if not rei_lock.acquire(blocking=False):
        return {"status": "already_running"}

    def single_pass():
        try:
            from utils.airtable_utils import read_records, update_record
            from utils.discord_utils import post_ops

            TABLE_REI = "Leads_REI"
            records = read_records(TABLE_REI)
            scored = 0

            for rec in records:
                fields = rec.get("fields", {})
                try:
                    arv = float(fields.get("ARV") or 0)
                    ask = float(fields.get("Ask") or 0)
                except (TypeError, ValueError):
                    continue

                if arv <= 0:
                    continue

                spread_ratio = (arv - ask) / arv
                sane = spread_ratio >= 0.05
                update_record(TABLE_REI, rec["id"], {"Price_Sanity_Flag": sane})
                scored += 1

            post_ops(f"REI single pass: scored {scored} leads")
        finally:
            rei_lock.release()

    t = threading.Thread(target=single_pass, daemon=True)
    t.start()

    return {"status": "ok", "message": "REI scoring started in background"}


@app.post("/trigger/govcon", tags=["engines_legacy"])
def trigger_govcon():
    """
    Manual trigger for GovCon scoring engine (single pass, non-blocking).
    Scores opportunities in GovCon Opportunities table.
    """
    from engines.govcon_engine import govcon_lock
    import threading

    if not govcon_lock.acquire(blocking=False):
        return {"status": "already_running"}

    def single_pass():
        try:
            from utils.airtable_utils import read_records, update_record
            from utils.discord_utils import post_ops

            TABLE_GOVCON = "GovCon Opportunities"
            records = read_records(TABLE_GOVCON)
            scored = 0

            for rec in records:
                fields = rec.get("fields", {})
                name = (fields.get("Opportunity Name") or "").strip()
                if not name:
                    continue

                try:
                    total_value = float(fields.get("Total Value") or 0)
                except (TypeError, ValueError):
                    total_value = 0.0

                score = min(100.0, total_value / 1000.0)
                update_record(TABLE_GOVCON, rec["id"], {"Hotness Score": score})
                scored += 1

            post_ops(f"GovCon single pass: scored {scored} opportunities")
        finally:
            govcon_lock.release()

    t = threading.Thread(target=single_pass, daemon=True)
    t.start()

    return {"status": "ok", "message": "GovCon scoring started in background"}


# =============================================================================
# KPI Endpoint
# =============================================================================

@app.post("/trigger/kpi", tags=["monitoring"])
def trigger_kpi():
    """Push KPI snapshot to Discord."""
    from utils.kpi import kpi_push
    return kpi_push()


# =============================================================================
# Main (for local dev)
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
