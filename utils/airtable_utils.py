import os
import json
import logging
import requests

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

def _headers():
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        raise RuntimeError("Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID")
    return {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }

def airtable_write(table: str, record: dict):
    """
    Create one record via Airtable REST.
    """
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table}"
    payload = {"records": [{"fields": record}], "typecast": True}
    resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data["records"][0] if "records" in data and data["records"] else data

# Back-compat alias if other modules import write_record
write_record = airtable_write

def safe_airtable_note(table: str, note: str, extra: dict | None = None):
    """
    Best-effort write. Never raises — logs errors only.
    Expects the table to have a 'Note' (or similar) text field; if your schema differs,
    adjust the field key below to match your base.
    """
    if not (AIRTABLE_API_KEY and AIRTABLE_BASE_ID):
        return False
    try:
        fields = {"Note": note}
        if extra:
            # Store extra as JSON text to avoid schema mismatch
            fields["Meta"] = json.dumps(extra, ensure_ascii=False)
        airtable_write(table, fields)
        return True
    except Exception as e:
        logging.warning(f"Airtable note failed: {e}")
        return False
