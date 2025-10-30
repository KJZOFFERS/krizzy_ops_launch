import asyncio
import time
from fastapi import FastAPI
from rei_dispo_engine import run_rei_dispo

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "running", "timestamp": int(time.time())}

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_rei_dispo())
