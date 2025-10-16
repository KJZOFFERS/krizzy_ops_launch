import asyncio
from utils.discord_utils import post_log


async def loop_forever(state: dict):
    while True:
        await post_log("✅ Watchdog heartbeat alive.")
        await asyncio.sleep(900)
