# src/common/discord_notify.py

import os
import requests

OPS_WEBHOOK = os.getenv("DISCORD_WEBHOOK_OPS")
ERROR_WEBHOOK = os.getenv("DISCORD_WEBHOOK_ERRORS")

def send_discord(message: str, channel: str = "ops"):
    """
    Send a plaintext Discord notification.
    channel = "ops" or "error"
    """
    webhook = OPS_WEBHOOK if channel == "ops" else ERROR_WEBHOOK

    if not webhook:
        print(f"[discord] missing webhook for channel={channel}")
        return False

    payload = {"content": message}

    try:
        r = requests.post(webhook, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[discord] error sending: {e}")
        return False
