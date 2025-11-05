# utils/airtable_utils.py
from __future__ import annotations
import os, httpx
from typing import Iterable, Optional, Dict, Any
from urllib.parse import quote

_API = "https://api.airtable.com/v0"

def _headers() -> Dict[str, str]:
    key = os.getenv("AIRTABLE_API_KEY")
    if not key:
        raise RuntimeError("AIRTABLE_API_KEY is not set")
    return {"Authorization": f"Bearer {key}"}

def _base_id() -> str:
    bid = os.getenv("AIRTABLE_BASE_ID")
    if not bid:
        raise RuntimeError("AIRTABLE_BASE_ID is not set")
    return bid

def list_records(
    table: str,
    view: Optional[str] = None,
    formula: Optional[str] = None,
    fields: Optional[Iterable[str]] = None,
    page_size: int = 100,
    max_records: Optional[int] = None,
) -> list[Dict[str, Any]]:
    base = _base_id()
    url = f"{_API}/{base}/{quote(table)}"
    params: Dict[str, Any] = {"pageSize": page_size}
    if view: params["view"] = view
    if formula: params["filterByFormula"] = formula
    if fields:
        for f in fields:
            params.setdefault("fields[]", []).append(f)

    out: list[Dict[str, Any]] = []
    offset = None
    with httpx.Client(timeout=15) as c:
        while True:
            q = dict(params)
            if offset: q["offset"] = offset
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
    """
    Create a single record. Returns {'id': 'rec...', 'fields': {...}, 'createdTime': '...'}
    """
    base = _base_id()
    url = f"{_API}/{base}/{quote(table)}"
    payload = {"fields": fields}
    with httpx.Client(timeout=15) as c:
        r = c.post(url, headers={**_headers(), "Content-Type": "application/json"}, json=payload)
        r.raise_for_status()
        return r.json()

