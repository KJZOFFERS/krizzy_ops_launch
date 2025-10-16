import os, aiohttp
WEBHOOK = os.getenv("DISCORD_WEBHOOK_OPS")


async def post_log(msg: str):
    if WEBHOOK:
        async with aiohttp.ClientSession() as s:
            await s.post(WEBHOOK, json={"content": msg})


async def post_error(msg: str):
    await post_log(f"🔴 {msg}")
