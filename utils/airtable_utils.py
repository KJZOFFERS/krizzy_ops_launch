from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional
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


def _quote_formula_value(v: str) -> str:
    # Escape backslashes then single quotes for Airtable formula literals
    v = v.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{v}'"


def list_records(
    table: str,
    view: Optional[str] = None,
    fields: Optional[Iterable[str]] = None,
    formula: Optional[str] = None,
    max_records: Optional[int] = None,
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {}
    if view:
        params["view"] = view
    if fields:
        for i, f in enumerate(fields):
            params[f"fields[{i}]"] = f
    if formula:
        params["filterByFormula"] = formula
    if max_records:
        params["maxRecords"] = max_records
    params["pageSize"] = page_size

    out: List[Dict[str, Any]] = []
    with httpx.Client(timeout=20) as c:
        url = _table_url(table)
        while True:
            r = c.get(url, headers=_headers(), params=params)
            r.raise_for_status()
            payload = r.json()
            out.extend(payload.get("records", []))
            offset = payload.get("offset")
            if not offset:
                break
            params["offset"] = offset
    return out


def create_record(table: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    with httpx.Client(timeout=15) as c:
        r = c.post(_table_url(table), headers=_headers(), json={"fields": fields})
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
    safe = _quote_formula_value(key_value)
    formula = f"{{{key_field}}} = {safe}"
    existing = list_records(table, formula=formula, max_records=1)
    if existing:
        rid = existing[0]["id"]
        return update_record(table, rid, fields)
    return create_record(table, {**fields, key_field: key_value})


def safe_airtable_write(
    table: str,
    fields: Dict[str, Any],
    key_field: Optional[str] = None,
    key_value: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Safe wrapper. If AIRTABLE_API_KEY or AIRTABLE_BASE_ID is missing, no-op and return None.
    If key_field and key_value are provided, do an upsert. Else create.
    """
    if not os.getenv("AIRTABLE_API_KEY") or not os.getenv("AIRTABLE_BASE_ID"):
        return None
    try:
        if key_field and key_value is not None:
            return upsert_record(table, key_field, key_value, fields)
        return create_record(table, fields)
    except Exception:
        return None

        fields=fields,
        page_size=page_size,
        max_records=max_records,
    )

