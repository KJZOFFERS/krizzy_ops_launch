import threading
import time
from typing import Any, Dict, List

from job_queue import enqueue_sync_airtable
from utils.airtable_utils import read_records
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
    if not record_id:
        return

    payload = {
        k: v
        for k, v in fields.items()
        if k in GOVCON_UPDATE_FIELDS and k in GOVCON_FIELDS
    }
    if not payload:
        return
    enqueue_sync_airtable(
        TABLE_GOVCON,
        payload,
        method="update",
        record_id=record_id,
    )


def run_govcon_engine(payload: Dict[str, Any] | None = None) -> None:
    """
    GovCon scoring engine.

    - Reads all GovCon Opportunities.
    - Computes Hotness Score from Total Value (simple baseline).
    - Writes Hotness Score only.
    """
    run_forever = bool(payload.get("loop_forever")) if isinstance(payload, dict) else False
    sleep_seconds = int(payload.get("sleep_seconds", 300)) if isinstance(payload, dict) else 300

    while True:
        if not govcon_lock.acquire(blocking=False):
            if not run_forever:
                return
            time.sleep(sleep_seconds)
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
            post_error(f"🔴 GovCon Engine Error: {type(e).__name__}: {e}")

        finally:
            govcon_lock.release()
            if not run_forever:
                return
            time.sleep(sleep_seconds)
