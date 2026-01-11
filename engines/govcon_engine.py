import threading
import time
from typing import Any, Dict, List

from utils.airtable_utils import read_records
from utils.airtable_meta import AirtableMetaCache
from utils.airtable_safe_upsert import AirtableSafeUpsert
from utils.codex import Codex
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


def _safe_upsert_govcon(
    safe: AirtableSafeUpsert,
    table_id: str,
    merge_field_id: str,
    merge_field_name: str,
    fields: Dict[str, Any],
) -> None:
    payload = {}
    if merge_field_name in (fields or {}):
        payload[merge_field_name] = fields[merge_field_name]
    payload.update(
        {
            k: v
            for k, v in (fields or {}).items()
            if k in GOVCON_UPDATE_FIELDS and k in GOVCON_FIELDS
        }
    )
    if not payload or merge_field_name not in payload:
        return
    safe.upsert(
        table_id=table_id,
        records=[{"fields": payload}],
        merge_field_id=merge_field_id,
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
            cx = Codex.load()
            meta = AirtableMetaCache(cx.AIRTABLE_PAT, cx.AIRTABLE_BASE_ID)
            safe = AirtableSafeUpsert(cx.AIRTABLE_PAT, cx.AIRTABLE_BASE_ID, meta)
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

                _safe_upsert_govcon(
                    safe,
                    cx.GOVCON_OPPS_TABLE_ID,
                    cx.GOVCON_MERGE_FIELD_ID,
                    "Opportunity Name",
                    {"Opportunity Name": name, "Hotness Score": score},
                )

        except Exception as e:
            post_error(f"🔴 GovCon Engine Error: {type(e).__name__}: {e}")

        finally:
            govcon_lock.release()
            if not run_forever:
                return
            time.sleep(sleep_seconds)
