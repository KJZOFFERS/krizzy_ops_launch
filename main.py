import asyncio, time
from fastapi import FastAPI
from validate_env import validate_env
from utils.watchdog import start_watchdog, uptime, lag
from utils.kpi import push
from engines.rei_dispo_engine import run_rei_cycle
from engines.govcon_subtrap_engine import run_govcon_cycle
from utils.data_extraction import run_data_cycle

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "ts": int(time.time())}

@app.get("/metrics")
async def metrics():
    return {"uptime": uptime(), "lag": lag()}

@app.on_event("startup")
async def startup():
    validate_env()
    asyncio.create_task(start_watchdog())
    asyncio.create_task(orchestrator())

async def orchestrator():
    while True:
        await run_data_cycle()
        await run_rei_cycle()
        await run_govcon_cycle()
        push("cycle_complete", {"status": "ok"})
        await asyncio.sleep(900)  # 15 min cycle

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
