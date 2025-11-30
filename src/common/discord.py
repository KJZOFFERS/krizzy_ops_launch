# src/common/discord.py
import os
import httpx

WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS")
WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS")


class DiscordOps:
    def __init__(self):
        if not WEBHOOK_OPS or not WEBHOOK_ERRORS:
            raise RuntimeError("Missing Discord webhooks.")

    async def send_ops(self, msg: str):
        async with httpx.AsyncClient() as client:
            await client.post(WEBHOOK_OPS, json={"content": msg})

    async def send_error(self, msg: str):
        async with httpx.AsyncClient() as client:
            await client.post(WEBHOOK_ERRORS, json={"content": f"⚠️ {msg}"})
