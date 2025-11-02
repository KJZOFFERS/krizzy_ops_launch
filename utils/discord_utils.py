import os
from typing import Optional
import httpx

OPS = os.getenv("DISCORD_WEBHOOK_OPS")
ERR = os.getenv("DISCORD_WEBHOOK_ERRORS")


async def _send(webhook: Optional[str], content: str) -> bool:
    if not webhook:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook, json={"content": content})
            return resp.status_code < 300
    except Exception:
        return False


async def post_ops(content: str) -> bool:
    return await _send(OPS, content)


async def post_error(content: str) -> bool:
    return await _send(ERR, content)
