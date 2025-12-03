import threading
import time
from utils.airtable_utils import read_records, update_record
from utils.discord_utils import post_ops, post_error

rei_lock = threading.Lock()

def run_rei_engine():
    while True:
        acquired = False
        if not rei_lock.acquire(blocking=False):
            time.sleep(60)
            continue
        acquired = True

        try:
            leads = read_records("Leads_REI", filter_formula="LEN({address}) > 0")
            fire = []

            required = ["key", "address", "ARV", "Ask"]

            for lead in leads:
                fields = lead.get("fields", {})
                
                # Skip records missing required fields
                if not all(fields.get(field) for field in required):
                    continue
                
                arv = fields.get("ARV") or 0
                ask = fields.get("Ask") or 0
                rep = fields.get("Repairs") or 0

                if arv == 0:
                    continue

                spread = arv - ask - rep
                score = (spread / arv) * 100

                update_record("Leads_REI", lead["id"], {
                    "Spread": spread,
                    "Score": score,
                    "Status": "SCANNED"
                })

                if score >= 70:
                    fire.append((score, fields))

            if fire:
                fire = sorted(fire, key=lambda x: x[0], reverse=True)[:3]
                post_ops(f"🔥 Top REI Deals:\n{fire}")

        except Exception as e:
            post_error(f"REI Engine Error: {e}")

        finally:
            if acquired:
                rei_lock.release()

        time.sleep(60)
