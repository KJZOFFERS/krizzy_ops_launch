from __future__ import annotations
from typing import Optional
from loguru import logger
try:
    import httpx  # type: ignore
except Exception:
    httpx = None
async def send_discord_message(webhook_url: Optional[str], content: str, embeds: list[dict] | None = None) -> bool:
    if not webhook_url or httpx is None:
        logger.debug("Discord send skipped (no webhook or offline).")
        return False
    payload = {"content": content}
    if embeds:
        payload["embeds"] = embeds
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(webhook_url, json=payload)
            return r.status_code < 400
    except Exception as e:
        logger.debug(f"Discord send failed/offline: {e}")
        return False
