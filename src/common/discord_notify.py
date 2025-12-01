# src/common/discord_notify.py
# Discord notifications + health status

import os
import requests
from typing import Dict


OPS_WEBHOOK = os.getenv("DISCORD_WEBHOOK_OPS")
ERROR_WEBHOOK = os.getenv("DISCORD_WEBHOOK_ERRORS")


def send_discord(message: str, channel: str = "ops") -> bool:
    """
    Send a plaintext Discord notification.
    channel = "ops" or "error"
    Never raises – returns False on failure.
    """
    webhook = OPS_WEBHOOK if channel == "ops" else ERROR_WEBHOOK

    if not webhook:
        print(f"[discord] missing webhook for channel={channel}")
        return False

    # Truncate if too long
    if len(message) > 1900:
        message = message[:1900] + "... [truncated]"

    payload = {"content": message}

    try:
        r = requests.post(webhook, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[discord] error sending: {e}")
        return False


def notify_ops(message: str) -> bool:
    """Shortcut: send to ops channel."""
    return send_discord(message, channel="ops")


def notify_error(message: str) -> bool:
    """Shortcut: send to error channel."""
    return send_discord(message, channel="error")


def get_webhook_status() -> Dict[str, str]:
    """
    Used by /health/deep to report Discord integration status.
    """
    return {
        "ops": "configured" if OPS_WEBHOOK else "not_configured",
        "errors": "configured" if ERROR_WEBHOOK else "not_configured",
    }
