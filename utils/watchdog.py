import asyncio, time
from .airtable_utils import upsert_record
from .discord_utils import send_discord

async def start_watchdog():
    while True:
        try:
            upsert_record("KPI_Log", "key", "heartbeat", {"status": "ok", "last_check": int(time.time())})
        except Exception as e:
            await send_discord("errors", f"Watchdog failure: {e!r}")
        await asyncio.sleep(60)
