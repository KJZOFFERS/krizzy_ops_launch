from fastapi import FastAPI
import asyncio
from utils.discord_utils import post_ops

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

async def _heartbeat():
    while True:
        try:
            post_ops("KRIZZY OPS: heartbeat OK")
        except Exception:
            pass
        await asyncio.sleep(300)

@app.on_event("startup")
async def on_start():
    app.state.hb = asyncio.create_task(_heartbeat())

@app.on_event("shutdown")
async def on_stop():
    task = getattr(app.state, "hb", None)
    if task:
        task.cancel()
