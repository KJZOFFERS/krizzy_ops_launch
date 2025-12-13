import os, time
from app_v2.database import SessionLocal
from app_v2.models.job import Job

def scheduler_loop():
    while True:
        db = SessionLocal()
        try:
            if os.getenv("OUTBOUND_ENABLED", "true").lower() == "true":
                db.add(Job(engine="rei", action="process_cycle"))
            if os.getenv("GOVCON_ENABLED", "true").lower() == "true":
                db.add(Job(engine="govcon", action="process_cycle"))
            db.commit()
        finally:
            db.close()
        time.sleep(60)
