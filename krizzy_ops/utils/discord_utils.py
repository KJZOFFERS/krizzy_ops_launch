import os,aiohttp
WEBHOOK=os.getenv("DISCORD_WEBHOOK_OPS")

async def post_log(msg):
    if WEBHOOK:
        async with aiohttp.ClientSession() as s: await s.post(WEBHOOK,json={"content":msg})

async def post_error(msg):
    await post_log(f"🔴 {msg}")
