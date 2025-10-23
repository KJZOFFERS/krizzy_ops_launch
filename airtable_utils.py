import hashlib
import logging
import os
from datetime import datetime
from typing import Any, Optional

import backoff
from pyairtable import Table
from pyairtable.api.types import RecordDict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
    logger.error("Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID environment variables")


def _get_table(table_name: str) -> Table:
    """Get Airtable table instance with proper error handling."""
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        raise ValueError("Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID")
    return Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, table_name)


@backoff.on_exception(
    backoff.expo,
    (Exception,),
    max_tries=3,
    jitter=backoff.random_jitter,
    giveup=lambda e: "429" not in str(e) and "5" not in str(e)[:1],
)
def safe_airtable_write(
    table_name: str, record: dict[str, Any], key_fields: list[str]
) -> Optional[RecordDict]:
    """
    Safely write to Airtable with upsert logic and proper error handling.

    Args:
        table_name: Name of the Airtable table
        record: Record data to write
        key_fields: Fields to use for deduplication

    Returns:
        Created or updated record, or None if failed
    """
    try:
        table = _get_table(table_name)

        # Create deduplication key from specified fields
        dedup_values = []
        for field in key_fields:
            value = record.get(field, "")
            if field in ["Phone", "Email"] and value:
                # Hash PII fields
                value = hashlib.sha256(str(value).encode()).hexdigest()[:16]
            dedup_values.append(str(value))

        dedup_key = "|".join(dedup_values)
        record["dedup_key"] = dedup_key

        # Try to find existing record
        try:
            existing_records = table.all(formula=f"{{dedup_key}} = '{dedup_key}'")
            if existing_records:
                # Update existing record
                existing_id = existing_records[0]["id"]
                updated_record = table.update(existing_id, record)
                logger.info(f"Updated existing record in {table_name}")
                return updated_record
        except Exception as e:
            logger.warning(f"Error checking for existing record: {e}")

        # Create new record
        new_record = table.create(record)
        logger.info(f"Created new record in {table_name}")
        return new_record

    except Exception as e:
        logger.error(f"Failed to write to {table_name}: {e}")
        return None


@backoff.on_exception(backoff.expo, (Exception,), max_tries=3, jitter=backoff.random_jitter)
def fetch_all(table_name: str) -> list[RecordDict]:
    """Fetch all records from a table with backoff."""
    try:
        table = _get_table(table_name)
        return table.all()
    except Exception as e:
        logger.error(f"Failed to fetch from {table_name}: {e}")
        return []


def add_record(table_name: str, data: dict) -> Optional[RecordDict]:
    """Legacy function for backward compatibility."""
    return safe_airtable_write(table_name, data, ["Source_URL", "Phone", "Email"])


def kpi_push(event: str, data: dict[str, Any]) -> None:
    """
    Push KPI event to Airtable with proper structure.

    Args:
        event: Event name (boot, cycle_start, cycle_end, error, etc.)
        data: Event data dictionary
    """
    kpi_record = {
        "Event": event,
        "Timestamp": datetime.utcnow().isoformat(),
        "Data": str(data),
        "Count": data.get("count", 0) if isinstance(data, dict) else 0,
        "Status": data.get("status", "success") if isinstance(data, dict) else "success",
    }

    result = safe_airtable_write("KPI_Log", kpi_record, ["Event", "Timestamp"])
    if result:
        logger.info(f"KPI logged: {event}")
    else:
        logger.error(f"Failed to log KPI: {event}")


# Legacy function for backward compatibility
def log_kpi(event: str, data: dict):
    """Legacy KPI logging function."""
    kpi_push(event, data)
