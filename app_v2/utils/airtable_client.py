import requests
from typing import List, Dict, Any, Optional
from app_v2 import config
from app_v2.utils.logger import get_logger

logger = get_logger(__name__)

API_BASE = "https://api.airtable.com/v0"
HEADERS = {
    "Authorization": f"Bearer {config.AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}


def read_records(
    table: str,
    filter_formula: Optional[str] = None,
    max_records: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Read records from Airtable table"""
    url = f"{API_BASE}/{config.AIRTABLE_BASE_ID}/{table}"
    params = {}

    if filter_formula:
        params["filterByFormula"] = filter_formula
    if max_records:
        params["maxRecords"] = max_records

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("records", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to read from {table}: {e}")
        raise


def write_record(table: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new record in Airtable table"""
    url = f"{API_BASE}/{config.AIRTABLE_BASE_ID}/{table}"
    payload = {"fields": fields}

    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to write to {table}: {e}")
        raise


def update_record(table: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing record in Airtable table"""
    url = f"{API_BASE}/{config.AIRTABLE_BASE_ID}/{table}/{record_id}"
    payload = {"fields": fields}

    try:
        response = requests.patch(url, headers=HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update {table}/{record_id}: {e}")
        raise


def batch_create(table: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch create records (max 10 per call per Airtable API)"""
    url = f"{API_BASE}/{config.AIRTABLE_BASE_ID}/{table}"
    created = []

    # Split into chunks of 10
    for i in range(0, len(records), 10):
        chunk = records[i:i + 10]
        payload = {"records": chunk}

        try:
            response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
            response.raise_for_status()
            created.extend(response.json().get("records", []))
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to batch create in {table}: {e}")
            raise

    return created
