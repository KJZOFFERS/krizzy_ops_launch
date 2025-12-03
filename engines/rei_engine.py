import threading
import time
from typing import Dict, Any

from utils.airtable_utils import read_records, update_record
from utils.discord_utils import post_error, post_ops

TABLE_REI = "Leads_REI"

# All known fields in the Leads_REI table
REI_FIELDS = {
    "key",
    "address",
    "ARV",
    "Ask",
    "Beds",
    "Baths",
    "SqFt",
    "DOM",
    "Source_URL",
    "Rent_Est",
    "School_Score",
    "Crime_Index",
    # computed fields – create these columns in Airtable once:
    "Spread",
    "Score",
}

rei_lock = threading.Lock()


def _safe_update_lead(record_id: str, fields: Dict[str, Any]) -> None:
    """Only send fields that actually exist in Airtable."""
    payload = {k: v for k, v in fields.items() if k in REI_FIELDS}
    if not payload:
        return
    update_record(TABLE_REI, record_id, payload)


def run_rei_engine() -> None:
    while True:
        if not rei_lock.acquire(blocking=False):
            time.sleep(60)
            continue

        try:
            records = read_records(TABLE_REI)

            top_deals = []

            for rec in records:
                fields = rec.get("fields", {})

                if not all(x in fields for x in ("address", "ARV", "Ask")):
                    continue

                try:
                    arv = float(fields.get("ARV") or 0)
                    ask = float(fields.get("Ask") or 0)
                except (TypeError, ValueError):
                    continue

                if arv <= 0:
                    continue

                # optional repairs – if the field doesn't exist or isn't numeric, treat as 0
                try:
                    repairs = float(fields.get("Repairs") or 0)
                except (TypeError, ValueError):
                    repairs = 0.0

                spread = arv - ask - repairs
                score = (spread / arv) * 100

                _safe_update_lead(rec["id"], {
                    "Spread": spread,
                    "Score": score,
                })

                top_deals.append((score, fields))

            # send top 3 to Discord
            top_deals = sorted(top_deals, key=lambda x: x[0], reverse=True)[:3]
            if top_deals:
                lines = []
                for score, f in top_deals:
                    addr = f.get("address", "Unknown")
                    arv = f.get("ARV")
                    ask = f.get("Ask")
                    lines.append(f"- {addr} | Score={score:.1f} | ARV={arv} | Ask={ask}")
                msg = "🔥 Top REI Deals:\n" + "\n".join(lines)
                post_ops(msg)

        except Exception as e:
            post_error(f"REI Engine Error: {e}")

        finally:
            rei_lock.release()
            time.sleep(60)
