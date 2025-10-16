import asyncio, time
from utils.discord_utils import post_log, post_error

async def loop_forever(state):
    while True:
        await post_log("✅ Watchdog heartbeat alive.")
        await asyncio.sleep(900)