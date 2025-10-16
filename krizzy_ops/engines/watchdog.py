import asyncio
from krizzy_ops.utils.discord_utils import post_log

async def loop_forever(state):
    while True:
        await post_log("✅ Watchdog heartbeat alive.")
        await asyncio.sleep(900)
