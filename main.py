
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
        app.state.engine_task = asyncio.create_task(run_engines())
    except Exception as e:
        post_error(f"Startup event failed: {e}")

async def run_engines():
    try:
        await asyncio.gather(
            rei_dispo_engine.loop_rei(),
            govcon_subtrap_engine.loop_govcon(),
            heartbeat()
        )
    except Exception as e:
        post_error(f"Engine loop failure: {e}")
