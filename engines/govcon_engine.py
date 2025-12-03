import threading
import time
from typing import Dict, Any

from utils.airtable_utils import read_records, update_record
from utils.discord_utils import post_error

TABLE_GOVCON = "GovCon Opportunities"

# Known fields in GovCon Opportunities
GOVCON_FIELDS = {
    "Opportunity Name",
    "Agency",
    "Total Value",
    "NAICS Code",
    "Set-Aside Type",
    "Submission Deadline",
    "Core Requirements",
    "Hotness Score",
    # optional dedup column – only used if you add it in Airtable
    "Dedup_Key",
}

govcon_lock = threading.Lock()


def _safe_update_govcon(record_id: str, fields: Dict[str, Any]) -> None:
    payload = {k: v for k, v in fields.items() if k in GOVCON_FIELDS}
    if not payload:
        return
    update_record(TABLE_GOVCON, record_id, payload)


def run_govcon_engine() -> None:
    while True:
        if not govcon_lock.acquire(blocking=False):
            time.sleep(300)
            continue

        try:
            records = read_records(TABLE_GOVCON)

            for rec in records:
                fields = rec.get("fields", {})

                name = (fields.get("Opportunity Name") or "").strip()
                try:
                    total_value = float(fields.get("Total Value") or 0)
                except (TypeError, ValueError):
                    total_value = 0.0

                if not name:
                    continue

                # simple scoring: higher value → higher score, capped at 100
                score = min(100.0, total_value / 1000.0)

                dedup_key = "".join(c for c in name.lower() if c.isalnum())

                _safe_update_govcon(rec["id"], {
                    "Hotness Score": score,
                    "Dedup_Key": dedup_key,
                })

        except Exception as e:
            post_error(f"GovCon Engine Error: {e}")

        finally:
            govcon_lock.release()
            time.sleep(300)
