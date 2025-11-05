# FILE: utils/airtable_utils.py
from typing import Iterable, Optional, Dict, Any, List
from urllib.parse import quote
import os
import httpx

try:
    from config import CFG
except Exception:
    CFG = None  # fallback to raw env

_API = "https://api.airtable.com/v0"

def _headers() -> Dict[str, str]:
    key = (CFG.AIRTABLE_API_KEY if CFG else None) or os.getenv("AIRTABLE_API_KEY")
    if not key:
        raise RuntimeError("AIRTABLE_API_KEY is not set")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

def _base_id() -> str:
    bid = (CFG.AIRTABLE_BASE_ID if CFG else None) or os.getenv("AIRTABLE_BASE_ID")
    if not bid:
        raise RuntimeError("AIRTABLE_BASE_ID is not set")
    return bid

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

def _escape_formula_value(val: Any) -> str:
    # Airtable formulas accept double-quoted strings; escape embedded double quotes.
    return str(val).replace('"', '\\"')

def upsert_record(table: str, key_field: str, key_value: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    # Use double quotes in formula to avoid single-quote escaping issues.
    # Example: {key} = "abc\"def"
    formula = f'{{{key_field}}} = "{_escape_formula_value(key_value)}"'
    existing = list_records(table, formula=formula, max_records=1)
    if existing:
        rid = existing[0]["id"]
        return update_record(table, rid, fields)
    return create_record(table, {**fields, key_field: key_value})

# --- safe write helpers ---

def safe_airtable_write(table: str, fields: Dict[str, Any], retries: int = 3) -> Dict[str, Any]:
    last_exc = None
    for _ in range(retries):
        try:
            return create_record(table, fields)
        except Exception as e:
            last_exc = e
    raise last_exc  # type: ignore[misc]

def safe_upsert(table: str, key_field: str, key_value: str, fields: Dict[str, Any], retries: int = 3) -> Dict[str, Any]:
    last_exc = None
    for _ in range(retries):
        try:
            return upsert_record(table, key_field, key_value, fields)
        except Exception as e:
            last_exc = e
    raise last_exc  # type: ignore[misc]

# --- table alias + fetch helpers ---

_TABLE_MAP: Dict[str, str] = {
    "Leads_REI": (CFG.AIRTABLE_TABLE_LEADS if CFG else None) or os.getenv("AIRTABLE_TABLE_LEADS", "Leads_REI"),
    "Buyers": (CFG.AIRTABLE_TABLE_BUYERS if CFG else None) or os.getenv("AIRTABLE_TABLE_BUYERS", "Buyers"),
    "GovCon_Opportunities": (CFG.AIRTABLE_TABLE_GOVCON if CFG else None) or os.getenv("AIRTABLE_TABLE_GOVCON", "GovCon_Opportunities"),
    "KPI_Log": (CFG.AIRTABLE_TABLE_KPI_LOG if CFG else None) or os.getenv("AIRTABLE_TABLE_KPI_LOG", "KPI_Log"),
}

def resolve_table(name: str) -> str:
    return _TABLE_MAP.get(name, name)

def fetch_table(
    table: str,
    *,
    view: Optional[str] = None,
    formula: Optional[str] = None,
    fields: Optional[Iterable[str]] = None,
    page_size: int = 100,
    max_records: Optional[int] = None,
) -> List[Dict[str, Any]]:
    return list_records(
        resolve_table(table),
        view=view,
        formula=formula,
        fields=fields,
        page_size=page_size,
        max_records=max_records,
    )

