import os, httpx, traceback as _tb

OPS_HOOK = os.getenv("DISCORD_OPS_WEBHOOK_URL")
ERR_HOOK = os.getenv("DISCORD_ERRORS_WEBHOOK_URL")

def _post_sync(url: str, payload: dict) -> None:
    if not url:
        return
    r = httpx.post(url, json=payload, timeout=10)
    r.raise_for_status()

async def _post_async(url: str, payload: dict) -> None:
    if not url:
        return
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(url, json=payload)
        r.raise_for_status()

def post_ops(msg: str) -> None:
    _post_sync(OPS_HOOK, {"content": msg})

def post_error(msg: str, exc: Exception | None = None) -> None:
    content = msg
    if exc:
        content += f"\n```{_tb.format_exc()}```"
    _post_sync(ERR_HOOK, {"content": content})

# requested by imports elsewhere
async def send_message(webhook_url: str, content: str) -> None:
    await _post_async(webhook_url, {"content": content})
