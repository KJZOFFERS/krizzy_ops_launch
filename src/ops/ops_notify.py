# src/ops/ops_notify.py

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import requests

DISCORD_WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS", "").strip()
DISCORD_WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS", "").strip() or DISCORD_WEBHOOK_OPS


def _post_discord(webhook_url: str, content: str) -> bool:
    """Post to Discord webhook"""
    if not webhook_url:
        return False
    try:
        resp = requests.post(
            webhook_url,
            json={"content": content[:1900]},
            timeout=10,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False


def send_ops(message: str) -> bool:
    """Send operational notification to OPS channel"""
    return _post_discord(DISCORD_WEBHOOK_OPS, message)


def send_health(summary: str, details: Optional[Dict[str, Any]] = None) -> bool:
    """Send health status to OPS channel"""
    ts = datetime.now(timezone.utc).isoformat()
    msg = f"💓 Health: {summary} | {ts}"
    if details:
        msg += f"\n```json\n{json.dumps(details, indent=2)[:800]}\n```"
    return _post_discord(DISCORD_WEBHOOK_OPS, msg)


def send_crack(engine: str, message: str, meta: Optional[Dict[str, Any]] = None) -> bool:
    """Send crack/error notification to ERRORS channel"""
    ts = datetime.now(timezone.utc).isoformat()
    msg = f"❌ CRACK | {engine} | {message} | {ts}"
    if meta:
        meta_str = json.dumps(meta, indent=2)[:500]
        msg += f"\n```json\n{meta_str}\n```"
    return _post_discord(DISCORD_WEBHOOK_ERRORS, msg)
