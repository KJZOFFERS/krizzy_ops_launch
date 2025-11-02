from typing import List, Optional, Union
from utils.safe import make_client, request_with_retries
from config import CFG

def _webhooks(raw: Optional[Union[str, List[str]]]) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    return [w for w in (raw or []) if isinstance(w, str) and w.startswith("http")]

def _post(content: str, targets: List[str]) -> None:
    if not targets:
        return
    client = make_client()
    payload = {"content": str(content)[:1900]}
    headers = {"Content-Type": "application/json"}
    for url in targets:
        def _do():
            return client.post(url, json=payload, headers=headers)
        request_with_retries(_do, service="discord")

def post_ops(msg: str) -> None:
    # Prefer OPS; if unset, try ERRORS
    targets = CFG.DISCORD_WEBHOOK_OPS or CFG.DISCORD_WEBHOOK_ERRORS
    _post(msg, _webhooks(targets))

def post_error(msg: str) -> None:
    # Prefer ERRORS; fallback to OPS
    targets = CFG.DISCORD_WEBHOOK_ERRORS or CFG.DISCORD_WEBHOOK_OPS
    _post("❌ " + str(msg), _webhooks(targets))

# Backward-compatible shim for old call sites.
# Accepted forms:
#   send_message("text")
#   send_message("text", webhooks="https://discord.com/api/webhooks/...")
#   send_message("text", webhooks=["...","..."])
#   send_message("text", channel="ops"|"errors")
def send_message(
    content: Union[str, int, float],
    webhooks: Optional[Union[str, List[str]]] = None,
    *,
    channel: str = "ops"
) -> None:
    content = str(content)
    targets: List[str] = []
    if webhooks:
        targets = _webhooks(webhooks)
    else:
        if channel.lower() in ("error", "errors"):
            targets = _webhooks(CFG.DISCORD_WEBHOOK_ERRORS or CFG.DISCORD_WEBHOOK_OPS)
        else:
            targets = _webhooks(CFG.DISCORD_WEBHOOK_OPS or CFG.DISCORD_WEBHOOK_ERRORS)
    _post(content, targets)

__all__ = ["post_ops", "post_error", "send_message"]
