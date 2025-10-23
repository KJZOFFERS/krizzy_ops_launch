import os
import hashlib
import logging
from typing import Dict, List, Optional, Any
from pyairtable import Table
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

class AirtableError(Exception):
    """Custom exception for Airtable operations"""
    pass

def _get_table(table_name: str) -> Table:
    """Get Airtable table instance"""
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        raise AirtableError("Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID")
    return Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, table_name)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, AirtableError))
)
def safe_airtable_write(table_name: str, record: Dict[str, Any], key_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Safely write to Airtable with upsert capability and backoff retry logic.
    
    Args:
        table_name: Name of the Airtable table
        record: Record data to write
        key_fields: Fields to use for deduplication (upsert)
    
    Returns:
        Created or updated record data
    """
    try:
        table = _get_table(table_name)
        
        # If key_fields provided, try to find existing record for upsert
        if key_fields:
            existing_records = table.all()
            for existing in existing_records:
                fields = existing.get("fields", {})
                if all(fields.get(key) == record.get(key) for key in key_fields if key in record):
                    # Update existing record
                    return table.update(existing["id"], record)
        
        # Create new record
        return table.create(record)
        
    except Exception as e:
        logger.error(f"Airtable write failed for table {table_name}: {e}")
        raise AirtableError(f"Failed to write to {table_name}: {e}")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, AirtableError))
)
def fetch_all(table_name: str) -> List[Dict[str, Any]]:
    """Fetch all records from Airtable table with retry logic"""
    try:
        table = _get_table(table_name)
        return table.all()
    except Exception as e:
        logger.error(f"Airtable fetch failed for table {table_name}: {e}")
        raise AirtableError(f"Failed to fetch from {table_name}: {e}")

def add_record(table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy function for backward compatibility"""
    return safe_airtable_write(table_name, data)

def create_dedup_key(record: Dict[str, Any], key_fields: List[str]) -> str:
    """Create a deduplication key from specified fields"""
    key_values = []
    for field in key_fields:
        value = record.get(field, "")
        if isinstance(value, str):
            # Create hash for phone/email fields
            if field.lower() in ["phone", "email"]:
                value = hashlib.md5(value.lower().strip().encode()).hexdigest()
        key_values.append(str(value))
    return "|".join(key_values)

def kpi_push(event: str, data: Dict[str, Any]) -> None:
    """Push KPI event to Airtable with error handling"""
    try:
        kpi_record = {
            "Event": event,
            "Data": str(data),
            "Timestamp": data.get("timestamp", ""),
            "Status": "success"
        }
        safe_airtable_write("KPI_Log", kpi_record)
        logger.info(f"KPI pushed: {event}")
    except Exception as e:
        logger.error(f"Failed to push KPI {event}: {e}")
        # Don't raise - KPI failures shouldn't break main flow
