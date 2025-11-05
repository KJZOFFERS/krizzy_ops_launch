# FILE: watchdog.py
import asyncio
from utils.discord_utils import post_ops

async def heartbeat():
    while True:
        try:
            post_ops("KRIZZY OPS heartbeat active")
        except Exception:
            pass
        await asyncio.sleep(60)
