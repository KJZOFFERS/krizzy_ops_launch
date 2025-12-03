import threading
import time
from typing import Dict, Any, List

from utils.airtable_utils import read_records, update_record
from utils.discord_utils import post_error, post_ops

TABLE_REI = "Leads_REI"

# Exact fields for Leads_REI from Airtable
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

# Only update this — it exists in Airtable
LEADS_REI_UPDATE_FIELDS = {"Price_Sanity_Flag"}

rei_lock = threading.Lock()


def _safe_update_lead(record_id: str, fields: Dict[str, Any]) -> None:
    payload = {
        k: v
        for k, v in fields.items()
        if k in LEADS_REI_UPDATE_FIELDS and k in LEADS_REI_FIELDS
    }
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

            ranked = []

            for rec in records:
                fields = rec.get("fields", {})

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

                # simple sanity flag
                sane = spread_ratio >= 0.05
                _safe_update_lead(rec["id"], {"Price_Sanity_Flag": sane})

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
                post_ops("🔥 Top REI Leads:\n" + "\n".join(lines))

        except Exception as e:
            post_error(f"REI Engine Error: {e}")

        finally:
            rei_lock.release()
            time.sleep(60)
