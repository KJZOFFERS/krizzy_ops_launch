import asyncio, os, time
from .airtable_utils import upsert
from .discord_utils import send_discord

_HEART = os.getenv("HEARTBEAT_TABLE", "KPI_Log")

async def start_watchdog():
    while True:
        try:
            upsert(_HEART, "key", "heartbeat", {"status":"ok","ts":int(time.time())})
        except Exception as e:
            await send_discord("errors", f"Watchdog heartbeat fail: {e!r}")
        await asyncio.sleep(60)
