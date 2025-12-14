import time
import os
from datetime import datetime
from app_v2.database import SessionLocal
from app_v2.models.ledger import Ledger
from app_v2.utils.logger import get_logger

logger = get_logger(__name__)


def run_worker_loop():
    """
    Autonomous execution kernel.
    Runs forever, writing heartbeat to ledger every N minutes.
    """
    interval_minutes = int(os.getenv("RUN_INTERVAL_MINUTES", "10"))
    interval_seconds = interval_minutes * 60

    logger.info(f"🚀 Worker starting - heartbeat interval: {interval_minutes} minutes")

    while True:
        db = SessionLocal()
        try:
            timestamp = datetime.utcnow().isoformat()

            logger.info(f"💓 Worker heartbeat tick at {timestamp}")

            entry = Ledger(
                engine="v2",
                action="worker_tick",
                reference_id=timestamp,
                value_estimate=0.0,
                cash_realized=0.0,
                cost=0.0,
                success=True
            )
            db.add(entry)
            db.commit()

            logger.info(f"✅ Heartbeat written to ledger successfully")

        except Exception as e:
            logger.error(f"❌ Worker heartbeat failed: {type(e).__name__}: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

        logger.info(f"⏳ Sleeping for {interval_minutes} minutes until next heartbeat...")
        time.sleep(interval_seconds)
