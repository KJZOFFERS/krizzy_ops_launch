import os
import requests
from datetime import datetime, timezone
from typing import Optional

DISCORD_WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS", "")
DISCORD_WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS", "") or DISCORD_WEBHOOK_OPS


def notify_ops(message: str) -> bool:
    if not DISCORD_WEBHOOK_OPS:
        return False
    try:
        r = requests.post(DISCORD_WEBHOOK_OPS, json={"content": message[:1900]}, timeout=8)
        return r.status_code in (200, 204)
    except Exception:
        return False


def notify_error(message: str) -> bool:
    if not DISCORD_WEBHOOK_ERRORS:
        return False
    try:
        r = requests.post(DISCORD_WEBHOOK_ERRORS, json={"content": message[:1900]}, timeout=8)
        return r.status_code in (200, 204)
    except Exception:
        return False


def log_crack(service: str, error: str, client=None) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    notify_error(f"CRACK | {service} | {error} | {ts}")
    if client:
        try:
            client.log_crack(service, error)
        except Exception:
            pass
