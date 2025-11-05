from __future__ import annotations
import os
import json
from typing import Iterable, Optional, Dict, Any, List
from urllib.parse import quote
import httpx

_API = "https://api.airtable.com/v0"

def _env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is not set")
    return v

def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {_env('AIRTABLE_API_KEY')}",
        "Content-Type": "application/json",
    }

def _table_url(table: str) -> str:
    base = _env("AIRTABLE_BASE_ID")
    return f"{_API}/{quote(base)}/{quote(table)}"

def list_records(
    table: str,
    fields: Optional[Iterable[str]] = None,
    formula: Optional[str] = None,
    max_records: Optional[int] = None,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {}
    if fields:
        params["fields[]"] = list(fields)
    if formula:
        params["filterByFormula"] = formula
    if max_records:
        params["maxRecords"] = max_records

    out: List[Dict[str, Any]] = []
    offset: Optional[str] = None
    with httpx.Client(timeout=15) as c:
        while True:
            qp = params.copy()
            if offset:
                qp["offset"] = offset
            r = c.get(_table_url(table), headers=_headers(), params=qp)
            r.raise_for_status()
            data = r.json()
            out.extend(data.get("records", []))
            if max_records and len(out) >= max_records:
                return out[:max_records]
            offset = data.get("offset")
            if not offset:
                return out

def create_record(table: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    url = _table_url(table)
    with httpx.Client(timeout=15) as c:
        r = c.post(url, headers=_headers(), json={"fields": fields})
        r.raise_for_status()
        return r.json()

def update_record(table: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{_table_url(table)}/{record_id}"
    with httpx.Client(timeout=15) as c:
        r = c.patch(url, headers=_headers(), json={"fields": fields})
        r.raise_for_status()
        return r.json()

def upsert_record(table: str, key_field: str, key_value: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    # Build a safe Airtable formula without backslash gymnastics
    # json.dumps returns a double-quoted, safely-escaped JSON string literal
    value_json = json.dumps(key_value)
    formula = f"{{{key_field}}} = {value_json}"

    existing = list_records(table, formula=formula, max_records=1)
    if existing:
        rid = existing[0]["id"]
        return update_record(table, rid, fields)
    return create_record(table, {**fields, key_field: key_value})

    try:
        return create_record(table, fields)
    except Exception:
        return None

