import os
import time


def run_worker_loop():
    """
    Autonomous execution kernel.
    DB interactions are disabled to keep startup DB-free.
    """

    interval_minutes = int(os.getenv("RUN_INTERVAL_MINUTES", "10"))
    interval_seconds = interval_minutes * 60

    while True:
        # Placeholder heartbeat without DB access
        time.sleep(interval_seconds)
