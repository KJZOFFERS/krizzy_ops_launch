from __future__ import annotations

import hashlib
import json
import os
import random
import time
from typing import Any, Dict, Iterable, List

import requests
from pyairtable import Table
from pyairtable.api.types import Record

# Required envs: AIRTABLE_API_KEY, AIRTABLE_BASE_ID
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

DEFAULT_TIMEOUT_SECONDS = 20
MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 1.0


def _jitter_delay(attempt: int) -> float:
    base = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
    return base + random.uniform(0, 0.5)


def _should_retry(status: int | None, exc: Exception | None) -> bool:
    if exc is not None:
        return True
    if status is None:
        return True
    if status == 429:
        return True
    if 500 <= status < 600:
        return True
    return False


def _get_table(table_name: str) -> Table:
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        raise RuntimeError("Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID")
    return Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, table_name)


def _escape_formula_value(value: Any) -> str:
    if value is None:
        return ""
    s = str(value)
    return s.replace("'", "\\'")


def _build_filter_formula(record: Dict[str, Any], key_fields: Iterable[str]) -> str:
    clauses: List[str] = []
    for key in key_fields:
        val = _escape_formula_value(record.get(key))
        clauses.append(f"{{{key}}}='{val}'")
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0]
    return "AND(" + ",".join(clauses) + ")"


def fetch_all(table_name: str) -> List[Record]:
    table = _get_table(table_name)
    attempt = 0
    while True:
        attempt += 1
        try:
            # pyairtable handles pagination internally with .all()
            return table.all(page_size=100)
        except Exception as exc:  # noqa: BLE001
            if attempt >= MAX_RETRIES:
                raise
            time.sleep(_jitter_delay(attempt))


def safe_airtable_write(table_name: str, record: Dict[str, Any], key_fields: Iterable[str]) -> Record:
    """Idempotent upsert into Airtable.

    - key_fields: list of field names that uniquely identify a record
    - Retries with backoff + jitter on 429/5xx or exceptions
    """
    table = _get_table(table_name)
    formula = _build_filter_formula(record, key_fields)
    attempt = 0
    last_status: int | None = None
    last_exc: Exception | None = None
    while True:
        attempt += 1
        try:
            existing: List[Record] = []
            if formula:
                existing = table.all(filterByFormula=formula, page_size=1)
            if existing:
                rec_id = existing[0]["id"]
                return table.update(rec_id, record, typecast=True)
            return table.create(record, typecast=True)
        except requests.HTTPError as http_exc:  # type: ignore[reportGeneralTypeIssues]
            last_status = getattr(http_exc.response, "status_code", None)
            last_exc = http_exc
        except Exception as exc:  # noqa: BLE001
            last_status = None
            last_exc = exc

        if attempt >= MAX_RETRIES or not _should_retry(last_status, last_exc):
            raise last_exc  # type: ignore[misc]
        time.sleep(_jitter_delay(attempt))


def compute_contact_hash(phone: str | None, email: str | None) -> str:
    phone_norm = (phone or "").strip().replace(" ", "")
    email_norm = (email or "").strip().lower()
    return hashlib.sha256((phone_norm + "|" + email_norm).encode("utf-8")).hexdigest()
