import time
import os
from datetime import datetime
from app_v2.database import SessionLocal
from app_v2.models.ledger import Ledger


def run_worker_loop():
    """
    Autonomous execution kernel.
    Runs forever, writing heartbeat to ledger every N minutes.
    """
    interval_minutes = int(os.getenv("RUN_INTERVAL_MINUTES", "10"))
    interval_seconds = interval_minutes * 60

    while True:
        db = SessionLocal()
        try:
            timestamp = datetime.utcnow().isoformat()

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

        except Exception as e:
            db.rollback()
        finally:
            db.close()

        time.sleep(interval_seconds)
