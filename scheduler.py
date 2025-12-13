import time
from models import Job

INTERVAL_SECONDS = 900  # 15 minutes

def scheduler_loop(db_factory):
    while True:
        db = db_factory()
        try:
            for engine in ["rei", "govcon"]:
                job = Job(
                    engine=engine,
                    step="run_pipeline",
                    payload={}
                )
                db.add(job)

            db.commit()
        except Exception as e:
            db.rollback()
            print("Scheduler error:", e)
        finally:
            db.close()

        time.sleep(INTERVAL_SECONDS)
