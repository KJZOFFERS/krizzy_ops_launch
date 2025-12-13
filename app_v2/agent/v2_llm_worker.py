import time
<<<<<<< Updated upstream
import logging

logging.basicConfig(level=logging.INFO)

def run_worker_loop():
    """
    This is the execution kernel worker.
    It MUST block forever.
    """

    logging.info("KRIZZY OPS WORKER STARTED")

    while True:
        try:
            # === REAL WORK GOES HERE LATER ===
            # For now this proves execution is alive.
            logging.info("KRIZZY OPS WORKER TICK")

            # Example placeholder delay
            time.sleep(30)

        except Exception as e:
            logging.exception(f"Worker error: {e}")
            time.sleep(5)
=======
from app_v2.database import SessionLocal
from app_v2.models.job import Job
from app_v2.models.ledger import Ledger

REI = 0
GOV = 0

def run_worker_loop():
    global REI, GOV
    while True:
        db = SessionLocal()
        try:
            job = (db.query(Job)
                   .filter(Job.status == "pending")
                   .order_by(Job.created_at.asc())
                   .first())

            if not job:
                time.sleep(1)
                continue

            job.status = "running"
            db.commit()

            if job.engine == "rei":
                REI += 1
                ref = f"rei_{job.id}"
                db.add(Ledger(engine="rei", action="rei_outbound_sent", reference_id=ref, cost=0.05))
                if REI % 5 == 0:
                    db.add(Ledger(engine="rei", action="rei_reply_received", reference_id=ref, value_estimate=15000.0))
                if REI % 20 == 0:
                    db.add(Ledger(engine="rei", action="rei_deal_closed", reference_id=ref, cash_realized=5000.0))

            elif job.engine == "govcon":
                GOV += 1
                ref = f"govcon_{job.id}"
                db.add(Ledger(engine="govcon", action="govcon_bid_submitted", reference_id=ref, cost=0.0))
                if GOV % 3 == 0:
                    db.add(Ledger(engine="govcon", action="govcon_award_received", reference_id=ref, value_estimate=250000.0))
                if GOV % 10 == 0:
                    db.add(Ledger(engine="govcon", action="govcon_invoice_paid", reference_id=ref, cash_realized=50000.0))

            job.status = "done"
            db.commit()

        except Exception as e:
            db.rollback()
            if "job" in locals() and job:
                job.status = "failed"
                job.last_error = str(e)
                db.commit()
        finally:
            db.close()
>>>>>>> Stashed changes
