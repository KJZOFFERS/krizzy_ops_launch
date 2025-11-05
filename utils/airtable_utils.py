# utils/airtable_utils.py
from __future__ import annotations
import os, httpx
from typing import Iterable, Optional, Dict, Any
from urllib.parse import quote

def _headers() -> Dict[str, str]:
    api_key = os.getenv("AIRTABLE_API_KEY")
    if not api_key:
        raise RuntimeError("AIRTABLE_API_KEY is not set")
    return {"Authorization": f"Bearer {api_key}"}

def _base_id() -> str:
    base_id = os.getenv("AIRTABLE_BASE_ID")
    if not base_id:
        raise RuntimeError("AIRTABLE_BASE_ID is not set")
    return base_id

def list_records(
    table: str,
    view: Optional[str] = None,
    formula: Optional[str] = None,
    fields: Optional[Iterable[str]] = None,
    page_size: int = 100,
    max_records: Optional[int] = None,
) -> list[Dict[str, Any]]:
    """
    Returns a list of Airtable record dicts: [{"id": "...","fields": {...}}, ...]
    """
    base_id = _base_id()
    url = f"https://api.airtable.com/v0/{base_id}/{quote(table)}"

    params: Dict[str, Any] = {"pageSize": page_size}
    if view:
        params["view"] = view
    if formula:
        params["filterByFormula"] = formula
    if fields:
        for f in fields:
            params.setdefault("fields[]", []).append(f)

    out: list[Dict[str, Any]] = []
    offset = None
    with httpx.Client(timeout=15) as client:
        while True:
            q = dict(params)
            if offset:
                q["offset"] = offset
            r = client.get(url, headers=_headers(), params=q)
            r.raise_for_status()
            data = r.json()
            recs = data.get("records", [])
            out.extend(recs)
            if max_records and len(out) >= max_records:
                return out[:max_records]
            offset = data.get("offset")
            if not offset:
                return out
