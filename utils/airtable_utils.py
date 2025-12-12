import os
import requests
from typing import Optional, Dict, Any, List

from utils.discord_utils import post_error

BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")
API_KEY = os.getenv("AIRTABLE_API_KEY", "")
API = "https://api.airtable.com/v0"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def _log_airtable_error(
    method: str,
    table: str,
    record_id: Optional[str],
    status_code: int,
    response_text: str,
    payload_fields: Optional[List[str]] = None
) -> None:
    """
    Log structured Airtable error details to Discord.
    """
    parts = [
        f"🚨 **Airtable {method} failed**",
        f"- Table: `{table}`",
        f"- Status: `{status_code}`",
    ]
    if record_id:
        parts.append(f"- Record ID: `{record_id}`")
    if payload_fields:
        parts.append(f"- Payload fields: `{', '.join(payload_fields)}`")
    parts.append(f"- Response: ```{response_text[:500]}```")
    post_error("\n".join(parts))


def read_records(table: str, formula: Optional[str] = None, filter_formula: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Read records from Airtable table with optional filterByFormula.
    Logs errors and re-raises on failure.
    """
    url = f"{API}/{BASE_ID}/{table}"
    params = {}
    if filter_formula:
        params["filterByFormula"] = filter_formula
    elif formula:
        params["filterByFormula"] = formula

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if not r.ok:
            _log_airtable_error("GET", table, None, r.status_code, r.text)
            r.raise_for_status()
        return r.json().get("records", [])
    except requests.exceptions.RequestException as e:
        # Network/timeout errors
        post_error(f"🚨 Airtable GET network error on table `{table}`: {e}")
        raise


def write_record(table: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new record in Airtable table.
    Logs errors and re-raises on failure.
    """
    url = f"{API}/{BASE_ID}/{table}"
    payload = {"fields": fields}
    field_keys = list(fields.keys())

    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        if not r.ok:
            _log_airtable_error("POST", table, None, r.status_code, r.text, field_keys)
            r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        post_error(f"🚨 Airtable POST network error on table `{table}` with fields `{', '.join(field_keys)}`: {e}")
        raise


def update_record(table: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing record in Airtable table.
    Logs errors and re-raises on failure.
    """
    url = f"{API}/{BASE_ID}/{table}/{record_id}"
    payload = {"fields": fields}
    field_keys = list(fields.keys())

    try:
        r = requests.patch(url, headers=HEADERS, json=payload, timeout=10)
        if not r.ok:
            _log_airtable_error("PATCH", table, record_id, r.status_code, r.text, field_keys)
            r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        post_error(f"🚨 Airtable PATCH network error on table `{table}`, record `{record_id}`, fields `{', '.join(field_keys)}`: {e}")
        raise
