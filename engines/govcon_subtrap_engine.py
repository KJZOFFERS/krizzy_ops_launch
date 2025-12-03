import threading
import time
from utils.airtable_utils import read_records, update_record
from utils.discord_utils import post_ops, post_error

TABLE_GOVCON = "GovCon Opportunities"

govcon_lock = threading.Lock()

def run_govcon_engine():
    while True:
        acquired = False
        if not govcon_lock.acquire(blocking=False):
            time.sleep(300)
            continue
        acquired = True

        try:
            opps = read_records(TABLE_GOVCON)

            for opp in opps:
                fields = opp.get("fields", {})
                sol = fields.get("Solicitation") or ""
                amount = fields.get("Value") or 0

                key = "".join(c for c in sol.lower() if c.isalnum())
                score = min(100, amount / 1000)

                update_record(TABLE_GOVCON, opp["id"], {
                    "Score": score,
                    "Dedup_Key": key
                })

        except Exception as e:
            post_error(f"GovCon Engine Error: {e}")

        finally:
            if acquired:
                govcon_lock.release()

        time.sleep(300)
