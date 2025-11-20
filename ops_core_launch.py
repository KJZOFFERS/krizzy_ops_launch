#!/usr/bin/env python3
"""
KRIZZY OPS 24/7 Core Launch Daemon
Runs REI SMS dispatch + GovCon feed ingestion on interval with health checks.
No FastAPI. No n8n. Direct execution only.
"""

import os
import sys
import time
import traceback
from datetime import datetime, timezone
import requests

try:
    from rei_dispo_engine import run_rei_engine
    from govcon_subtrap_engine import run_govcon_engine
except ImportError as e:
    print(f"[FATAL] Missing engine module: {e}")
    sys.exit(1)


def send_discord(webhook_url, message, level="INFO"):
    if not webhook_url:
        return
    color_map = {
        "INFO": 3447003,
        "SUCCESS": 3066993,
        "ERROR": 15158332,
        "HEARTBEAT": 10181046,
    }
    payload = {
        "embeds": [{
            "title": f"🤖 KRIZZY OPS | {level}",
            "description": message,
            "color": color_map.get(level, 3447003),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    }
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        print(f"[WARN] Discord send failed: {e}")


def health_check():
    webhook = os.getenv("DISCORD_WEBHOOK_OPS")
    uptime_minutes = (time.time() - START_TIME) / 60
    message = (
        f"✅ **24/7 Core Running**\n"
        f"Uptime: {uptime_minutes:.1f} minutes\n"
        f"Interval: {RUN_INTERVAL_MINUTES} min\n"
        f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_discord(webhook, message, level="HEARTBEAT")


def main_loop():
    cycle_count = 0
    while True:
        cycle_count += 1
        cycle_start = time.time()

        print(f"\n{'='*60}")
        print(f"[CYCLE {cycle_count}] {datetime.now(timezone.utc).isoformat()}")
        print(f"{'='*60}\n")

        if cycle_count % 5 == 1:
            health_check()

        # REI
        try:
            print("[REI ENGINE] Starting...")
            rei_result = run_rei_engine()
            send_discord(os.getenv("DISCORD_WEBHOOK_OPS"),
                         f"✅ REI Engine: {rei_result}",
                         level="SUCCESS")
        except Exception:
            error_msg = f"❌ REI Engine crashed:\n```{traceback.format_exc()[:1500]}```"
            send_discord(os.getenv("DISCORD_WEBHOOK_ERRORS"),
                         error_msg,
                         level="ERROR")
            print(error_msg)

        # GOVCON
        try:
            print("[GOVCON ENGINE] Starting...")
            govcon_result = run_govcon_engine()
            send_discord(os.getenv("DISCORD_WEBHOOK_OPS"),
                         f"✅ GovCon Engine: {govcon_result}",
                         level="SUCCESS")
        except Exception:
            error_msg = f"❌ GovCon Engine crashed:\n```{traceback.format_exc()[:1500]}```"
            send_discord(os.getenv("DISCORD_WEBHOOK_ERRORS"),
                         error_msg,
                         level="ERROR")
            print(error_msg)

        elapsed = time.time() - cycle_start
        sleep_seconds = max(0, (RUN_INTERVAL_MINUTES * 60) - elapsed)

        print(f"\n[CYCLE {cycle_count}] Completed in {elapsed:.1f}s")
        print(f"[SLEEP] {sleep_seconds:.0f}s\n")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    required = ["AIRTABLE_API_KEY", "AIRTABLE_BASE_ID"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"[FATAL] Missing required env vars: {missing}")
        sys.exit(1)

    RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "15"))
    START_TIME = time.time()

    send_discord(os.getenv("DISCORD_WEBHOOK_OPS"),
                 f"🚀 **KRIZZY OPS CORE LAUNCHED**\n"
                 f"Interval: {RUN_INTERVAL_MINUTES} minutes\n"
                 f"Engines: REI_DISPO + GOVCON_SUBTRAP\n"
                 f"Mode: 24/7 Autonomous",
                 level="INFO")

    try:
        main_loop()
    except KeyboardInterrupt:
        send_discord(os.getenv("DISCORD_WEBHOOK_OPS"),
                     "🛑 **KRIZZY OPS CORE STOPPED** (manual shutdown)",
                     level="INFO")
        sys.exit(0)
    except Exception:
        send_discord(os.getenv("DISCORD_WEBHOOK_ERRORS"),
                     f"💀 **FATAL CRASH**\n```{traceback.format_exc()[:1500]}```",
                     level="ERROR")
        sys.exit(1)
