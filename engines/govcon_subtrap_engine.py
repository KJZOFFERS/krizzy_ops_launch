import threading
import time
from utils.airtable_utils import read_records, update_record
from utils.discord_utils import post_ops, post_error

govcon_lock = threading.Lock()

def run_govcon_engine():
    if not govcon_lock.acquire(blocking=False):
        return

    try:
        opps = read_records("GovCon_Opportunities")

        for opp in opps:
            fields = opp.get("fields", {})
            sol = fields.get("Solicitation") or ""
            amount = fields.get("Value") or 0

            key = "".join(c for c in sol.lower() if c.isalnum())
            score = min(100, amount / 1000)

            update_record("GovCon_Opportunities", opp["id"], {
                "Score": score,
                "Dedup_Key": key
            })

    except Exception as e:
        post_error(f"GovCon Engine Error: {e}")

    finally:
        govcon_lock.release()
