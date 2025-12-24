import time

from job_queue import enqueue_engine_run

INTERVAL_SECONDS = 900  # 15 minutes


def scheduler_loop(db_factory):
    while True:
        for engine in ["rei", "govcon", "deal_closer"]:
            try:
                enqueue_engine_run(engine)
            except Exception as e:  # noqa: BLE001
                print("Scheduler error:", e)

        time.sleep(INTERVAL_SECONDS)
