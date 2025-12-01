# src/engines/rei_engine.py
# REI Dispo Engine - hardened

from typing import Dict, Any, Optional


async def run_rei_engine(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    REI Dispo Engine - processes real estate leads from Airtable.
    - Never raises exceptions to FastAPI.
    - Handles both old and new AirtableClient APIs (get() or fetch()).
    """
    from src.common.airtable_client import get_airtable
    from src.common.discord_notify import notify_ops, notify_error

    if payload is None:
        payload = {}

    airtable = get_airtable()
    if airtable is None:
        msg = "Airtable not configured (AIRTABLE_API_KEY / AIRTABLE_BASE_ID missing)"
        notify_error(f"🚨 REI Engine: {msg}")
        return {
            "status": "error",
            "engine": "REI_DISPO",
            "error": msg,
        }

    try:
        # Support both APIs: fetch() (preferred) or get()
        if hasattr(airtable, "fetch"):
            records = await airtable.fetch("Leads_REI")
        else:
            # Fallback if only get() exists
            data = await airtable.get("Leads_REI")  # type: ignore[attr-defined]
            if isinstance(data, dict):
                records = data.get("records", [])
            else:
                records = data

        count = len(records) if isinstance(records, list) else 0

        notify_ops(f"🏠 REI Engine executed | {count} leads pulled from Leads_REI")

        return {
            "status": "ok",
            "engine": "REI_DISPO",
            "leads_processed": count,
            "records": records,
        }

    except Exception as e:
        # Catch httpx.ReadTimeout and all other issues
        notify_error(f"🚨 REI Engine failed: {e}")
        return {
            "status": "error",
            "engine": "REI_DISPO",
            "error": str(e),
        }
