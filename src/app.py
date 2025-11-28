import asyncio
from fastapi import FastAPI

from src.rei_dispo_engine import main as rei_loop
from src.govcon_subtrap_engine import main as govcon_loop
from src.ops_health_service import main as ops_health_loop

app = FastAPI(title="KRIZZY OPS")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "engines": {
            "rei": "running",
            "govcon": "running",
            "ops_health": "running",
        }
    }

async def run_rei():
    await asyncio.to_thread(rei_loop)

async def run_govcon():
    await asyncio.to_thread(govcon_loop)

async def run_ops_health():
    await asyncio.to_thread(ops_health_loop)

@app.on_event("startup")
async def start_workers():
    loop = asyncio.get_event_loop()
    loop.create_task(run_rei())
    loop.create_task(run_govcon())
    loop.create_task(run_ops_health())
