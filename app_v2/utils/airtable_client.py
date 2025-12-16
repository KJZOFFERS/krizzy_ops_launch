import requests
from typing import List, Dict, Any, Optional
from app_v2 import config
from app_v2.utils.logger import get_logger
from app_v2.utils.airtable_schema import filter_fields, refresh_schema

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
    filtered = filter_fields(fields, table, config.AIRTABLE_BASE_ID, config.AIRTABLE_API_KEY)
    payload = {"fields": filtered}

    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        if response.status_code == 422:
            logger.warning(f"Airtable 422 on POST to {table}: {response.text}")
            refresh_schema(config.AIRTABLE_BASE_ID, config.AIRTABLE_API_KEY)
            filtered = filter_fields(fields, table, config.AIRTABLE_BASE_ID, config.AIRTABLE_API_KEY)
            payload = {"fields": filtered}
            response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to write to {table}: {e}")
        raise


def update_record(table: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing record in Airtable table"""
    url = f"{API_BASE}/{config.AIRTABLE_BASE_ID}/{table}/{record_id}"
    filtered = filter_fields(fields, table, config.AIRTABLE_BASE_ID, config.AIRTABLE_API_KEY)
    payload = {"fields": filtered}

    try:
        response = requests.patch(url, headers=HEADERS, json=payload, timeout=10)
        if response.status_code == 422:
            logger.warning(f"Airtable 422 on PATCH to {table}/{record_id}: {response.text}")
            refresh_schema(config.AIRTABLE_BASE_ID, config.AIRTABLE_API_KEY)
            filtered = filter_fields(fields, table, config.AIRTABLE_BASE_ID, config.AIRTABLE_API_KEY)
            payload = {"fields": filtered}
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

    for i in range(0, len(records), 10):
        chunk = records[i:i + 10]
        filtered_chunk = [
            {"fields": filter_fields(r.get("fields", r), table, config.AIRTABLE_BASE_ID, config.AIRTABLE_API_KEY)}
            for r in chunk
        ]
        payload = {"records": filtered_chunk}

        try:
            response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
            if response.status_code == 422:
                logger.warning(f"Airtable 422 on batch create to {table}: {response.text}")
                refresh_schema(config.AIRTABLE_BASE_ID, config.AIRTABLE_API_KEY)
                filtered_chunk = [
                    {"fields": filter_fields(r.get("fields", r), table, config.AIRTABLE_BASE_ID, config.AIRTABLE_API_KEY)}
                    for r in chunk
                ]
                payload = {"records": filtered_chunk}
                response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
            response.raise_for_status()
            created.extend(response.json().get("records", []))
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to batch create in {table}: {e}")
            raise

    return created
