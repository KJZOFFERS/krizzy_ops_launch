import os, requests, asyncio
WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS")
WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS")

async def send_discord_message(channel_type, message):
    url = WEBHOOK_ERRORS if channel_type == "errors" else WEBHOOK_OPS
    if not url:
        return
    data = {"content": message[:1900]}
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, requests.post, url, data)
    except Exception:
        pass
