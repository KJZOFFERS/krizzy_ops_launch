import asyncio, datetime
from discord_utils import send_discord_message

async def watchdog_loop():
    while True:
        try:
            await send_discord_message("ops",
                f"Watchdog heartbeat {datetime.datetime.utcnow().isoformat()}")
        except Exception:
            pass
        await asyncio.sleep(1800)
