from __future__ import annotations

import datetime
import os
import random
import time
from typing import Dict

import requests

from airtable_utils import fetch_all
from discord_utils import post_err, post_ops

MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 1.0


def _jitter_delay(attempt: int) -> float:
    base = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
    return base + random.uniform(0, 0.5)


def _rotate_proxy() -> None:
    url = os.getenv("PROXY_ROTATE_URL")
    if not url:
        post_ops("Proxy rotation skipped: no PROXY_ROTATE_URL configured")
        return
    try:
        r = requests.post(url, timeout=10)
        post_ops(f"Proxy rotation HTTP {r.status_code}")
    except Exception as e:  # noqa: BLE001
        post_err(f"Proxy rotation failed: {e}")


def _check_loop(url: str) -> Dict[str, int]:
    stats = {"ok": 0, "throttle": 0, "errors": 0}
    attempt = 0
    while True:
        attempt += 1
        try:
            r = requests.post(url, timeout=30)
            if r.status_code == 200:
                stats["ok"] += 1
                return stats
            if r.status_code == 429:
                stats["throttle"] += 1
                if attempt >= MAX_RETRIES:
                    return stats
                time.sleep(_jitter_delay(attempt))
                continue
            if r.status_code == 403 or 500 <= r.status_code < 600:
                stats["errors"] += 1
                if attempt == 3:
                    _rotate_proxy()
                if attempt >= MAX_RETRIES:
                    return stats
                time.sleep(_jitter_delay(attempt))
                continue
            return stats
        except Exception:
            if attempt >= MAX_RETRIES:
                return stats
            time.sleep(_jitter_delay(attempt))


def run_watchdog() -> Dict[str, int]:
    # Validate data sanity
    cleaned = 0
    for t in ["Leads_REI", "GovCon_Opportunities"]:
        try:
            records = fetch_all(t)
        except Exception:
            records = []
        for r in records:
            f = r.get("fields", {})
            if not f.get("Source_URL") and not f.get("source_id"):
                cleaned += 1

    # Restart loops if failure detected via HTTP endpoints
    port = int(os.environ.get("PORT", "8080"))
    base = f"http://127.0.0.1:{port}"
    rei_stats = _check_loop(f"{base}/ops/rei")
    govcon_stats = _check_loop(f"{base}/ops/govcon")

    result = {
        "cleaned": cleaned,
        "rei_ok": rei_stats.get("ok", 0),
        "govcon_ok": govcon_stats.get("ok", 0),
        "throttle": rei_stats.get("throttle", 0) + govcon_stats.get("throttle", 0),
        "errors": rei_stats.get("errors", 0) + govcon_stats.get("errors", 0),
    }
    post_ops(
        f"Watchdog {datetime.datetime.utcnow().isoformat()} | cleaned={cleaned} throttle={result['throttle']} errors={result['errors']}"
    )
    return result
