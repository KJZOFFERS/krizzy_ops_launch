from __future__ import annotations
import os
from typing import Iterable, Optional, Dict, Any, List
from urllib.parse import quote
import httpx

_API = "https://api.airtable.com/v0"

def _get(name: str) -> Optional[str]:
    return os.getenv(name)

def _need(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is not set")
    return v

def _headers() -> Dict[str, str]:
    key = _need("AIRTABLE_API_KEY")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

def _base() -> str:
    return _need("AIRTABLE_BASE_ID")

def _table_url(table: str) -> str:
    return f"{_API}/{quote(_base())}/{quote(table)}"

def list_records(
    table: str,
    formula: Optional[str] = None,
    fields: Optional[Iterable[str]] = None,
    view: Optional[str] = None,
    max_records: int = 100,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {}
    if formula:
        params["filterByFormula"] = formula
    if fields:
        for i, f in enumerate(fields):
            params[f"fields[{i}]"] = f
    if view:
        params["view"] = view
    if max_records:
        params["maxRecords"] = max_records

    out: List[Dict[str, Any]] = []
    offset = None
    with httpx.Client(timeout=20) as c:
        while True:
            p = dict(params)
            if offset:
                p["offset"] = offset
            r = c.get(_table_url(table), headers=_headers(), params=p)
            r.raise_for_status()
            data = r.json()
            out.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset or (max_records and len(out) >= max_records):
                return out[:max_records] if max_records else out

def create_record(table: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    with httpx.Client(timeout=20) as c:
        r = c.post(_table_url(table), headers=_headers(), json={"fields": fields})
        r.raise_for_status()
        return r.json()

def update_record(table: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    with httpx.Client(timeout=20) as c:
        r = c.patch(f"{_table_url(table)}/{record_id}", headers=_headers(), json={"fields": fields})
        r.raise_for_status()
        return r.json()

def upsert_record(table: str, key_field: str, key_value: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    # Avoid backslashes inside f-string expressions (Python 3.13 rule)
    esc = key_value.replace("'", "\\'")
    formula = f"{{{key_field}}} = '{esc}'"
    existing = list_records(table, formula=formula, max_records=1)
    if existing:
        rid = existing[0]["id"]
        return update_record(table, rid, fields)
    return create_record(table, {**fields, key_field: key_value})

def fetch_table(table: str, limit: int = 100) -> List[Dict[str, Any]]:
    try:
        return list_records(table, max_records=limit)
    except Exception:
        return []

def safe_airtable_write(table: str, fields: Dict[str, Any]):
    if not _get("AIRTABLE_BASE_ID") or not _get("AIRTABLE_API_KEY"):
        return None
    try:
        return create_record(table, fields)
    except Exception:
        return None

