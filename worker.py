# FILE: worker.py
import asyncio
from utils.discord_utils import post_ops

def notify(msg: str):
    try:
        post_ops(msg)
    except Exception:
        pass

async def worker_loop():
    while True:
        notify("KRIZZY OPS worker running...")
        await asyncio.sleep(60)
