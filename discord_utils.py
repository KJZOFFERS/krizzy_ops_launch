from __future__ import annotations

import os
import random
import time
from typing import Optional

import requests

OPS = os.getenv("DISCORD_WEBHOOK_OPS")
ERR = os.getenv("DISCORD_WEBHOOK_ERRORS")

MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 1.0


def _jitter_delay(attempt: int) -> float:
    base = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
    return base + random.uniform(0, 0.5)


def _post(webhook_url: Optional[str], content: str) -> None:
    if not webhook_url:
        return
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.post(webhook_url, json={"content": content}, timeout=10)
            if resp.status_code in (200, 204):
                return
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                if attempt >= MAX_RETRIES:
                    return
                time.sleep(_jitter_delay(attempt))
                continue
            return
        except Exception:
            if attempt >= MAX_RETRIES:
                return
            time.sleep(_jitter_delay(attempt))


def post_ops(msg: str) -> None:
    _post(OPS, f"✅ {msg}")


def post_err(msg: str) -> None:
    _post(ERR, f"❌ {msg}")
