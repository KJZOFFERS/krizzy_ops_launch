import time
from models import Job, Ledger

MAX_ATTEMPTS = 3

def run_pipeline(engine, db):
    # THIS IS INTENTIONALLY SIMPLE
    # REAL LOGIC CAN CHANGE LATER WITHOUT TOUCHING INFRA

    ledger_entry = Ledger(
        engine=engine,
        record_id="system",
        action="pipeline_run",
        value_estimate=0,
        cash_realized=0,
        cost=0
    )
    db.add(ledger_entry)

def worker_loop(db_factory):
    while True:
        db = db_factory()
        try:
            job = (
                db.query(Job)
                .filter(Job.status == "pending")
                .order_by(Job.created_at.asc())
                .first()
            )

            if not job:
                time.sleep(5)
                continue

            job.status = "running"
            db.commit()

            run_pipeline(job.engine, db)

            job.status = "done"
            db.commit()

        except Exception as e:
            db.rollback()
            job.attempts += 1
            job.last_error = str(e)
            job.status = "failed" if job.attempts >= MAX_ATTEMPTS else "pending"
            db.commit()

        finally:
            db.close()
