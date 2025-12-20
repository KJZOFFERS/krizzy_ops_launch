import logging
import threading
import time
from typing import Any, Dict, List

from utils.airtable_utils import read_records, update_record
from utils.discord_utils import post_error, post_ops

logger = logging.getLogger("krizzy_ops_launch.rei_engine")

TABLE_REI = "Leads_REI"

# Exact fields for Leads_REI from Airtable schema
LEADS_REI_FIELDS: List[str] = [
    "key",
    "address",
    "ARV",
    "Ask",
    "Beds",
    "Baths",
    "SqFt",
    "Lot_SqFt",
    "Repairs_Note",
    "Comps_JSON",
    "DOM",
    "Source_URL",
    "Geo_Lat",
    "Geo_Lng",
    "Rent_Est",
    "School_Score",
    "Crime_Index",
    "Price_Sanity_Flag",
    "Ingest_TS",
]

# Only this field is updated by the engine (it exists in Airtable)
LEADS_REI_UPDATE_FIELDS = {"Price_Sanity_Flag"}

rei_lock = threading.Lock()


def _safe_update_lead(record_id: str, fields: Dict[str, Any]) -> None:
    """
    Only send fields that exist in Leads_REI and are in our update whitelist.
    This guarantees no 422 from invalid field names.
    """
    if not record_id:
        return

    payload = {
        k: v
        for k, v in (fields or {}).items()
        if k in LEADS_REI_UPDATE_FIELDS and k in LEADS_REI_FIELDS
    }
    if not payload:
        return

    try:
        update_record(TABLE_REI, record_id, payload)
    except Exception as e:
        logger.exception("Airtable update failed for record %s", record_id)
        post_error(f"🔴 REI Engine Update Error: {type(e).__name__}: {e}")


def run_rei_engine(payload: Dict[str, Any] | None = None) -> None:
    """
    REI sanity / ranking engine.

    - Reads all records from Leads_REI.
    - Computes spread_ratio = (ARV - Ask) / ARV when ARV > 0.
    - Sets Price_Sanity_Flag = True if spread_ratio >= 5%.
    - Sends top 3 by spread_ratio to Discord.
    - Never writes any field that isn't in Airtable schema.
    """
    logger.info("rei engine started with payload: %s", payload or {})

    run_forever = bool(payload.get("loop_forever")) if isinstance(payload, dict) else False
    sleep_seconds = int(payload.get("sleep_seconds", 60)) if isinstance(payload, dict) else 60

    while True:
        if not rei_lock.acquire(blocking=False):
            if not run_forever:
                return
            time.sleep(sleep_seconds)
            continue

        try:
            records = read_records(TABLE_REI)
            if not isinstance(records, list):
                records = []
            ranked = []

            for rec in records:
                fields = rec.get("fields") or {}
                record_id = rec.get("id")

                if "ARV" not in fields or "Ask" not in fields:
                    continue

                try:
                    arv = float(fields.get("ARV") or 0)
                    ask = float(fields.get("Ask") or 0)
                except (TypeError, ValueError):
                    continue

                if arv <= 0:
                    continue

                spread = arv - ask
                spread_ratio = spread / arv

                sane = spread_ratio >= 0.05  # 5%+ spread is "sane"
                _safe_update_lead(record_id, {"Price_Sanity_Flag": sane})

                ranked.append((spread_ratio, fields))

            ranked.sort(key=lambda x: x[0], reverse=True)
            top = ranked[:3]

            if top:
                lines = []
                for ratio, f in top:
                    addr = f.get("address", "Unknown")
                    arv = f.get("ARV")
                    ask = f.get("Ask")
                    lines.append(
                        f"- {addr} | spread_ratio={ratio:.2%} | ARV={arv} | Ask={ask}"
                    )
                post_ops("🔥 Top REI Leads_REI (by spread):\n" + "\n".join(lines))

            logger.info("rei engine completed cycle; records_processed=%s", len(records))

        except Exception as e:
            logger.exception("rei engine encountered an error")
            post_error(f"🔴 REI Engine Error: {type(e).__name__}: {e}")

        finally:
            if rei_lock.locked():
                rei_lock.release()
            if not run_forever:
                logger.info("rei engine finished single run")
                return
            time.sleep(sleep_seconds)

