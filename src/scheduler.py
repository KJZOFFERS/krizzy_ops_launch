# APSCHEDULER DISABLED — Thread engine is active.
# Enable in the future by uncommenting scheduler.start().

from apscheduler.schedulers.background import BackgroundScheduler
from src.engines.rei_engine import run_rei_engine
from src.engines.govcon_engine import run_govcon_engine


scheduler = BackgroundScheduler()


# Example job registration (disabled)
# scheduler.add_job(run_rei_engine, "interval", minutes=1)
# scheduler.add_job(run_govcon_engine, "interval", minutes=5)


def start_scheduler():
    # scheduler.start()  # DISABLED
    pass

