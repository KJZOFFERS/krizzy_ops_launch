# utils/__init__.py
# Compatibility layer so existing imports work.
import os
import json
import time
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus
import requests

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AT_TABLE_KPI = os.getenv("AIRTABLE_KPI_TABLE", os.getenv("AT_TABLE_KPI", "KPI_Log"))

def _api_base() -> str:
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        raise RuntimeError("Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID")
    return f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"

def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def create_record(table: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{_api_base()}/{quote_plus(table)}"
    payload = {"records": [{"fields": fields}]}
    r = requests.post(url, headers=_headers(), data=json.dumps(payload), timeout=15)
    r.raise_for_status()
    data = r.json()
    return data["records"][0]

def update_record(table: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{_api_base()}/{quote_plus(table)}/{record_id}"
    payload = {"fields": fields}
    r = requests.patch(url, headers=_headers(), data=json.dumps(payload), timeout=15)
    r.raise_for_status()
    return r.json()

def list_records(table: str, max_records: int = 1000) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    url = f"{_api_base()}/{quote_plus(table)}"
    params: Dict[str, Any] = {"pageSize": 100}
    while True:
        r = requests.get(url, headers=_headers(), params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        out.extend(data.get("records", []))
        if "offset" not in data or len(out) >= max_records:
            break
        params["offset"] = data["offset"]
    return out

def kpi_log(engine: str, action: str, details: str = "", ref: Optional[str] = None) -> None:
    fields = {
        "Timestamp": now_iso(),
        "Engine": engine,
        "Action": action,
        "Details": details,
    }
    if ref:
        fields["LeadID or OpportunityID"] = ref
    try:
        create_record(AT_TABLE_KPI, fields)
    except Exception:
        # Never crash on KPI write
        pass
