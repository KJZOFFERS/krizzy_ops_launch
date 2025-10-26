import os, json, aiohttp, asyncio

_WEBHOOKS = {
    "ops": os.getenv("DISCORD_WEBHOOK_OPS", ""),
    "errors": os.getenv("DISCORD_WEBHOOK_ERRORS", ""),
    "trades": os.getenv("DISCORD_WEBHOOK_TRADES", ""),
}

async def send_discord(channel: str, text: str):
    url = _WEBHOOKS.get(channel, "")
    if not url:  # silent no-op to avoid crashing engines
        return
    payload = {"content": text[:1900]}
    timeout = aiohttp.ClientTimeout(total=8)
    async with aiohttp.ClientSession(timeout=timeout) as sess:
        async with sess.post(url, data=payload) as r:
            if r.status >= 400:
                # minimal backoff
                await asyncio.sleep(2)
                await sess.post(url, data=payload)
