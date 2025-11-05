import os
import logging
import httpx
from typing import Dict, Any, List, Optional

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")
_API_ROOT = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"

_client = httpx.Client(timeout=15.0, headers={"Authorization": f"Bearer {AIRTABLE_API_KEY}"})

def _escape_single_quotes(v: str) -> str:
    return v.replace("'", "\\'")

def _eq_formula(field: str, value: str) -> str:
    return f"{{{field}}} = '{_escape_single_quotes(value)}'"

def list_records(table: str, formula: Optional<StringError := str] = None, max_records: int = 100) -> List[Dict[str, Any]]:
    """List records with optional filterByFormula. Returns raw Airtable records."""
    params = {}
    if formula:
        params["filterByFormula"] = formula
    records: List[Dict[str, Any]] = []
    offset = None
    fetched = 0
    while True:
        if offset:
            params["offset"] = offset
        resp = _client.get(f"{_API_ROOT}/{table}", params=params)
        resp.raise_for_status()
        data = resp.json()
        chunk = data.get("records", [])
        records.extend(chunk)
        fetched += len(chunk)
        if fetched >= max_records or "offset" not in data:
            break
        offset = data["offset"]
    return records[:max_records]

def create_record(table: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    resp = _client.post(f"{_API_ROOT}/{table}", json={"fields": fields})
    resp.raise_for_status()
    return resp.json()

def update_record(table: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    resp = _client.patch(f"{_API_ROOT}/{table}/{record_id}", json={"fields": fields})
    resp.raise_for_status()
    return resp.json()

def upsert_record(table: str, key_field: str, key_value: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Find by key_field==key_value. Update first hit or create."""
    formula = _eq_formula(key_field, str(key_value))
    existing = list_records(table, formula=formula, max_records=1)
    if existing:
        rid = existing[0]["id"]
        return update_record(table, rid, fields)
    return create_record(table, fields)
