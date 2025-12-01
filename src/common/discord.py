import os
import httpx

async def send_discord(message: str):
    url = os.getenv("DISCORD_WEBHOOK_OPS")
    if not url:
        return {"error": "Discord not configured"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"content": message})
