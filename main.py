
import os, asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from engines import rei_dispo_engine, govcon_subtrap_engine
from utils.discord_utils import post_ops, post_error
from utils.airtable_utils import fetch_table
from utils.watchdog import heartbeat

app = FastAPI()

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})

@app.on_event("startup")
async def startup_event():
    try:
        post_ops("Starting KRIZZY OPS engines...")
        # save tasks to prevent garbage collection
        app.state.rei_task = asyncio.create_task(rei_dispo_engine.loop_rei())
        app.state.govcon_task = asyncio.create_task(govcon_subtrap_engine.loop_govcon())
        app.state.watchdog_task = asyncio.create_task(heartbeat())
    except Exception as e:
        post_error(f"Startup event failed: {e}")
