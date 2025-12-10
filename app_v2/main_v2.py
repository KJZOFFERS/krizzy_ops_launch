from fastapi import FastAPI
from app_v2 import config
from app_v2.models.system_state import system_state
from app_v2.loop_orchestrator import start_orchestrator
from app_v2.thread_supervisor import supervisor
from app_v2.utils.logger import get_logger

# Import engines
from app_v2.engines.underwriting_engine import underwriting_loop

logger = get_logger(__name__)

app = FastAPI(title="KRIZZY OPS V2", version="2.0.0")


@app.on_event("startup")
async def startup():
    """Initialize system on startup"""
    logger.info("Starting KRIZZY OPS V2 system...")

    # Start dynamic interval orchestrator
    start_orchestrator()

    # Register engines with supervisor
    supervisor.register_engine("underwriting", underwriting_loop)
    # TODO: Register other engines as they're built

    # Start all engines
    supervisor.start_all_engines()

    # Start health check supervisor
    supervisor.start_supervisor()

    logger.info("KRIZZY OPS V2 system fully operational")


@app.get("/health")
def health():
    """System health check"""
    return {
        "status": "ok",
        "version": "2.0.0",
        "system_state": system_state.get_status()
    }


@app.get("/metrics")
def metrics():
    """System metrics"""
    return system_state.get_status()


@app.post("/trigger/underwriting")
def trigger_underwriting():
    """Manual trigger for underwriting engine (one cycle)"""
    from app_v2.engines.underwriting_engine import run_underwriting_cycle
    result = run_underwriting_cycle()
    return {"status": "ok", **result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
