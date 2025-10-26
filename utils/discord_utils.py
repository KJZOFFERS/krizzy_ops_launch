import os, aiohttp, asyncio

_WEBHOOKS = {
    "ops": os.getenv("DISCORD_WEBHOOK_OPS", ""),
    "errors": os.getenv("DISCORD_WEBHOOK_ERRORS", ""),
    "trades": os.getenv("DISCORD_WEBHOOK_TRADES", "")
}

async def send_discord(channel: str, text: str):
    url = _WEBHOOKS.get(channel, "")
    if not url:
        return
    payload = {"content": text[:1900]}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, timeout=10) as r:
                if r.status >= 400:
                    await asyncio.sleep(2)
                    await s.post(url, json=payload)
    except Exception:
        pass
