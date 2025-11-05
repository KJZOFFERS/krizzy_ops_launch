from __future__ import annotations
import os
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

def _base_id() -> str:
    return _env("AIRTABLE_BASE_ID")

def _table_url(table: str) -> str:
    return f"{_API}/{_base_id()}/{quote(table)}"

def list_records(
    table: str,
    view: Optional[str] = None,
    formula: Optional[str] = None,
    fields: Optional[Iterable[str]] = None,
    page_size: int = 100,
    max_records: Optional[int] = None,
) -> List[Dict[str, Any]]:
    url = _table_url(table)
    params: Dict[str, Any] = {"pageSize": page_size}
    if view:
        params["view"] = view
    if formula:
        params["filterByFormula"] = formula
    if fields:
        for f in fields:
            params.setdefault("fields[]", []).append(f)

    out: List[Dict[str, Any]] = []
    offset = None
    with httpx.Client(timeout=15) as c:
        while True:
            q = dict(params)
            if offset:
                q["offset"] = offset
            r = c.get(url, headers=_headers(), params=q)
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
    # Find by {key_field} = key_value; create if absent, else update
    formula = f"{{{key_field}}} = '{key_value.replace(\"'\",\"\\'\")}'"
    existing = list_records(table, formula=formula, max_records=1)
    if existing:
        rid = existing[0]["id"]
        return update_record(table, rid, fields)
    return create_record(table, {**fields, key_field: key_value})
