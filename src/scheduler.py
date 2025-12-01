# src/scheduler.py
# 24/7 Background Scheduler for KRIZZY OPS
#
# Runs REI and GovCon engines on configurable intervals.
# Env vars:
#   REI_INTERVAL_MINUTES (default: 15)
#   GOVCON_INTERVAL_MINUTES (default: 30)
#   SCHEDULER_ENABLED (default: true)

import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.common.discord_notify import notify_ops, notify_error


# Config from env
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
REI_INTERVAL = int(os.getenv("REI_INTERVAL_MINUTES", "15"))
GOVCON_INTERVAL = int(os.getenv("GOVCON_INTERVAL_MINUTES", "30"))


scheduler = AsyncIOScheduler()


async def scheduled_rei():
    """Run REI engine on schedule."""
    from src.engines.rei_engine import run_rei_engine
    try:
        result = await run_rei_engine()
        status = result.get("status", "unknown")
        processed = result.get("leads_processed", 0)
        high_score = result.get("high_score", 0)
        
        if status == "error":
            notify_error(f"⏰ Scheduled REI failed: {result.get('error')}")
        # Summary already sent by engine, no duplicate needed
    except Exception as e:
        notify_error(f"⏰ Scheduled REI CRASHED: {e}")


async def scheduled_govcon():
    """Run GovCon engine on schedule."""
    from src.engines.govcon_engine import run_govcon_engine
    try:
        result = await run_govcon_engine()
        status = result.get("status", "unknown")
        
        if status == "error":
            notify_error(f"⏰ Scheduled GovCon failed: {result.get('error')}")
    except Exception as e:
        notify_error(f"⏰ Scheduled GovCon CRASHED: {e}")


def start_scheduler():
    """
    Initialize and start the background scheduler.
    Call this from app startup.
    """
    if not SCHEDULER_ENABLED:
        print("[scheduler] Disabled via SCHEDULER_ENABLED=false")
        return

    # REI Engine - every N minutes
    scheduler.add_job(
        scheduled_rei,
        trigger=IntervalTrigger(minutes=REI_INTERVAL),
        id="rei_engine_job",
        name="REI Dispo Engine",
        replace_existing=True,
        max_instances=1  # Prevent overlap
    )

    # GovCon Engine - every N minutes
    scheduler.add_job(
        scheduled_govcon,
        trigger=IntervalTrigger(minutes=GOVCON_INTERVAL),
        id="govcon_engine_job",
        name="GovCon Sub-Trap Engine",
        replace_existing=True,
        max_instances=1
    )

    scheduler.start()

    notify_ops(
        f"⏰ KRIZZY OPS Scheduler ONLINE\n"
        f"REI: every {REI_INTERVAL}m | GovCon: every {GOVCON_INTERVAL}m"
    )
    print(f"[scheduler] Started - REI every {REI_INTERVAL}m, GovCon every {GOVCON_INTERVAL}m")


def stop_scheduler():
    """Graceful shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("[scheduler] Stopped")
