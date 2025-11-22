# src/common/airtable_utils.py
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "").strip()
AIRTABLE_BASE_ID_RAW = os.getenv("AIRTABLE_BASE_ID", "").strip()

API_ROOT = "https://api.airtable.com/v0"
META_ROOT = "https://api.airtable.com/v0/meta"

class AirtableError(RuntimeError):
    pass

def _headers() -> Dict[str, str]:
    if not AIRTABLE_API_KEY:
        raise AirtableError("Missing AIRTABLE_API_KEY")
    return {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }

def normalize_base_id(base_id_raw: str) -> str:
    """
    Accepts:
      - appXXXXXXXXXXXXXX
      - https://airtable.com/appXXXXXXXXXXXXXX/...
      - https://api.airtable.com/v0/appXXXXXXXXXXXXXX/...
    Returns base id only.
    """
    if not base_id_raw:
        raise AirtableError("Missing AIRTABLE_BASE_ID")

    if base_id_raw.startswith("app"):
        return base_id_raw

    m = re.search(r"(app[a-zA-Z0-9]{14,})", base_id_raw)
    if m:
        return m.group(1)

    raise AirtableError(f"Could not normalize base id from: {base_id_raw}")

AIRTABLE_BASE_ID = normalize_base_id(AIRTABLE_BASE_ID_RAW)

def _request(
    method: str,
    url: str,
    retries: int = 5,
    backoff_s: float = 1.5,
    timeout: int = 30,
    **kwargs
) -> requests.Response:
    last_err = None
    for i in range(retries):
        try:
            r = requests.request(method, url, headers=_headers(), timeout=timeout, **kwargs)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(backoff_s * (i + 1))
                continue
            r.raise_for_status()
            return r
        except Exception as e:
            last_err = e
            time.sleep(backoff_s * (i + 1))
    raise AirtableError(f"Airtable request failed after {retries} tries: {last_err}")

def meta_tables() -> List[Dict[str, Any]]:
    url = f"{META_ROOT}/bases/{AIRTABLE_BASE_ID}/tables"
    r = _request("GET", url)
    data = r.json()
    return data.get("tables", [])

def get_table_schema(table_name: str) -> Dict[str, Any]:
    tables = meta_tables()
    for t in tables:
        if t.get("name") == table_name:
            return t
    raise AirtableError(f"Table not found in base schema: {table_name}")

def get_field_names(table_name: str) -> List[str]:
    schema = get_table_schema(table_name)
    return [f.get("name") for f in schema.get("fields", [])]

def list_records(
    table_name: str,
    max_records: int = 50,
    view: Optional[str] = None,
    fields: Optional[List[str]] = None,
    filter_by_formula: Optional[str] = None,
) -> List[Dict[str, Any]]:
    url = f"{API_ROOT}/{AIRTABLE_BASE_ID}/{table_name}"
    params: Dict[str, Any] = {"maxRecords": max_records}
    if view:
        params["view"] = view
    if fields:
        for i, f in enumerate(fields):
            params[f"fields[{i}]"] = f
    if filter_by_formula:
        params["filterByFormula"] = filter_by_formula

    out: List[Dict[str, Any]] = []
    offset = None
    while True:
        if offset:
            params["offset"] = offset
        r = _request("GET", url, params=params)
        payload = r.json()
        out.extend(payload.get("records", []))
        offset = payload.get("offset")
        if not offset or len(out) >= max_records:
            break
    return out[:max_records]

def create_records(table_name: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not records:
        return []
    url = f"{API_ROOT}/{AIRTABLE_BASE_ID}/{table_name}"
    r = _request("POST", url, json={"records": records})
    return r.json().get("records", [])

def update_records(table_name: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not records:
        return []
    url = f"{API_ROOT}/{AIRTABLE_BASE_ID}/{table_name}"
    r = _request("PATCH", url, json={"records": records})
    return r.json().get("records", [])

def safe_airtable_write(
    table_name: str,
    unique_field: str,
    incoming: List[Dict[str, Any]],
) -> Tuple[int, int]:
    """
    Idempotent upsert by unique_field.
    Returns (created_count, updated_count).
    """
    if not incoming:
        return (0, 0)

    # Pull existing unique values
    existing = list_records(table_name, max_records=10000, fields=[unique_field])
    existing_map = {}
    for rec in existing:
        val = (rec.get("fields") or {}).get(unique_field)
        if val is not None:
            existing_map[str(val)] = rec.get("id")

    to_create = []
    to_update = []

    for item in incoming:
        fields = item.get("fields", {})
        uval = fields.get(unique_field)
        if uval is None:
            continue
        key = str(uval)
        rec_id = existing_map.get(key)
        if rec_id:
            to_update.append({"id": rec_id, "fields": fields})
        else:
            to_create.append({"fields": fields})

    created = 0
    updated = 0

    # Airtable batch limit 10
    for i in range(0, len(to_create), 10):
        batch = to_create[i:i+10]
        created += len(create_records(table_name, batch))

    for i in range(0, len(to_update), 10):
        batch = to_update[i:i+10]
        updated += len(update_records(table_name, batch))

    return (created, updated)
