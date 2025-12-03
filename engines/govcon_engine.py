import threading
import time
from typing import Dict, Any, List

from utils.airtable_utils import read_records, update_record
from utils.discord_utils import post_error

TABLE_GOVCON = "GovCon Opportunities"

# Exact fields for GovCon Opportunities from Airtable schema
GOVCON_FIELDS: List[str] = [
    "Opportunity Name",
    "Agency",
    "Total Value",
    "NAICS Code",
    "Set-Aside Type",
    "Submission Deadline",
    "Core Requirements",
    "Opportunity Summary",
    "Opportunity Photo",
    "Region",
    "GovCon Partners",
    "Scoring Notes",
    "Hotness Score",
    "Top Subcontractor Matches",
    "Days Until Deadline",
    "Partner Count",
    "Partner NAICS Match Count",
    "Summary Output",
    "Opportunity Score (AI)",
]

# Only this field is updated by the engine (it exists in Airtable)
GOVCON_UPDATE_FIELDS = {"Hotness Score"}

govcon_lock = threading.Lock()


def _safe_update_govcon(record_id: str, fields: Dict[str, Any]) -> None:
    """
    Only send fields that exist in GovCon Opportunities and are in our update whitelist.
    This guarantees no 422 from invalid field names.
    """
    payload = {
        k: v
        for k, v in fields.items()
        if k in GOVCON_UPDATE_FIELDS and k in GOVCON_FIELDS
    }
    if not payload:
        return
    update_record(TABLE_GOVCON, record_id, payload)


def run_govcon_engine() -> None:
    """
    GovCon scoring engine.

    - Reads all GovCon Opportunities.
    - Computes Hotness Score from Total Value (simple baseline).
    - Writes Hotness Score only.
    """
    while True:
        if not govcon_lock.acquire(blocking=False):
            time.sleep(300)
            continue

        try:
            records = read_records(TABLE_GOVCON)

            for rec in records:
                fields = rec.get("fields", {})

                name = (fields.get("Opportunity Name") or "").strip()
                if not name:
                    continue

                try:
                    total_value = float(fields.get("Total Value") or 0)
                except (TypeError, ValueError):
                    total_value = 0.0

                score = min(100.0, total_value / 1000.0)

                _safe_update_govcon(rec["id"], {"Hotness Score": score})

        except Exception as e:
            post_error(f"GovCon Engine Error: {e}")

        finally:
            govcon_lock.release()
            time.sleep(300)
