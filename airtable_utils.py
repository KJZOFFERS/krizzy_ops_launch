"""Airtable utilities with idempotent writes and retry logic."""

import os
import time
import random
import hashlib
from typing import Dict, List, Any, Optional
from pyairtable import Table
from requests.exceptions import HTTPError


AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")


def _exponential_backoff_with_jitter(
    attempt: int, base_delay: float = 1.0, max_delay: float = 32.0
) -> float:
    """Calculate exponential backoff with jitter."""
    delay = min(base_delay * (2**attempt), max_delay)
    jitter = random.uniform(0, min(delay * 0.1, max_delay - delay))
    return min(delay + jitter, max_delay)


def _should_retry(exception: Exception) -> bool:
    """Determine if exception is retryable."""
    if isinstance(exception, HTTPError):
        status_code = exception.response.status_code if exception.response else 0
        return status_code in (429, 500, 502, 503, 504)
    return False


def _hash_key(value: str) -> str:
    """Generate consistent hash for deduplication."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def safe_airtable_write(
    table_name: str, record: Dict[str, Any], key_fields: List[str], max_retries: int = 5
) -> Optional[Dict[str, Any]]:
    """
    Idempotent write to Airtable with upsert logic.

    Args:
        table_name: Airtable table name
        record: Record data to write
        key_fields: List of field names to use for deduplication
        max_retries: Maximum number of retry attempts

    Returns:
        Created or updated record, or None on failure
    """
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        return None

    table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, table_name)

    for attempt in range(max_retries):
        try:
            dedupe_key_parts = [str(record.get(field, "")) for field in key_fields]
            dedupe_key = _hash_key("".join(dedupe_key_parts))
            record["_dedupe_key"] = dedupe_key

            existing = table.all(formula=f"{{_dedupe_key}}='{dedupe_key}'")

            if existing:
                record_id = existing[0]["id"]
                return table.update(record_id, record)
            else:
                return table.create(record)

        except Exception as e:
            if _should_retry(e) and attempt < max_retries - 1:
                delay = _exponential_backoff_with_jitter(attempt)
                time.sleep(delay)
                continue
            return None

    return None


def fetch_all(table_name: str, max_retries: int = 3) -> List[Dict[str, Any]]:
    """
    Fetch all records from Airtable table with retry logic.

    Args:
        table_name: Airtable table name
        max_retries: Maximum number of retry attempts

    Returns:
        List of records
    """
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        return []

    table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, table_name)

    for attempt in range(max_retries):
        try:
            return table.all()
        except Exception as e:
            if _should_retry(e) and attempt < max_retries - 1:
                delay = _exponential_backoff_with_jitter(attempt)
                time.sleep(delay)
                continue
            return []

    return []


def add_record(
    table_name: str, record: Dict[str, Any], max_retries: int = 5
) -> Optional[Dict[str, Any]]:
    """
    Add record to Airtable with retry logic.

    Args:
        table_name: Airtable table name
        record: Record data
        max_retries: Maximum number of retry attempts

    Returns:
        Created record or None on failure
    """
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        return None

    table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, table_name)

    for attempt in range(max_retries):
        try:
            return table.create(record)
        except Exception as e:
            if _should_retry(e) and attempt < max_retries - 1:
                delay = _exponential_backoff_with_jitter(attempt)
                time.sleep(delay)
                continue
            return None

    return None
