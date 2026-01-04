"""
Airtable-safe upsert helper with:
- Schema intersection (Meta API)
- Idempotent performUpsert using External_Id fieldId fallback
- 429 backoff handling
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from app_v2.utils.logger import get_logger

logger = get_logger(__name__)

META_URL = "https://api.airtable.com/v0/meta/bases/{base_id}/tables"
TABLE_URL = "https://api.airtable.com/v0/{base_id}/{table_id}"

SCHEMA_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}
SCHEMA_TTL_SECONDS = 300


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def fetch_table_schema(base_id: str, table_id: str, token: str, *, force: bool = False) -> Dict[str, Any]:
    cache_key = (base_id, table_id)
    cached = SCHEMA_CACHE.get(cache_key)
    now = time.time()
    if cached and not force and (now - cached.get("_ts", 0)) < SCHEMA_TTL_SECONDS:
        return cached

    resp = requests.get(META_URL.format(base_id=base_id), headers=_auth_headers(token), timeout=15)
    resp.raise_for_status()
    data = resp.json()
    schema: Dict[str, Any] = {}
    for table in data.get("tables", []):
        if table.get("id") != table_id:
            continue
        fields = table.get("fields", [])
        name_to_id = {field["name"]: field["id"] for field in fields if field.get("name") and field.get("id")}
        id_to_name = {v: k for k, v in name_to_id.items()}
        schema = {
            "name": table.get("name"),
            "name_to_id": name_to_id,
            "id_to_name": id_to_name,
            "allowed": set(name_to_id.keys()) | set(id_to_name.keys()),
            "_ts": now,
        }
        break

    if not schema:
        raise ValueError(f"Table id {table_id} not found in base {base_id}")

    SCHEMA_CACHE[cache_key] = schema
    return schema


def _intersect_fields(
    fields: Dict[str, Any], schema: Dict[str, Any]
) -> Dict[str, Any]:
    allowed = schema["allowed"]
    cleaned: Dict[str, Any] = {}
    for key, value in fields.items():
        if value is None:
            continue
        if key in allowed:
            cleaned[key] = value
        elif key in schema["name_to_id"]:
            cleaned[schema["name_to_id"][key]] = value
    return cleaned


def _perform_upsert(
    base_id: str,
    table_id: str,
    token: str,
    records: List[Dict[str, Any]],
    merge_field: str,
) -> List[Dict[str, Any]]:
    url = TABLE_URL.format(base_id=base_id, table_id=table_id)
    payload = {
        "performUpsert": {"fieldsToMergeOn": [merge_field]},
        "records": [{"fields": r} for r in records],
    }
    resp = requests.post(url, headers=_auth_headers(token), json=payload, timeout=30)
    if resp.status_code == 429:
        raise RateLimitError(resp)
    if resp.status_code == 422:
        raise SchemaError(resp)
    resp.raise_for_status()
    return resp.json().get("records", [])


class RateLimitError(Exception):
    def __init__(self, response: requests.Response):
        self.response = response
        super().__init__(f"Airtable 429: {response.text}")


class SchemaError(Exception):
    def __init__(self, response: requests.Response):
        self.response = response
        super().__init__(f"Airtable 422: {response.text}")


def upsert_records(
    *,
    base_id: str,
    table_id: str,
    token: str,
    records: List[Dict[str, Any]],
    merge_field_id: str,
    fallback_field_id: Optional[str] = None,
    max_retries: int = 3,
    backoff_seconds: int = 30,
) -> List[Dict[str, Any]]:
    """
    Upsert records in batches of 10 with schema intersection and 429 backoff.
    """
    if not records:
        return []

    schema = fetch_table_schema(base_id, table_id, token)
    saved: List[Dict[str, Any]] = []
    for i in range(0, len(records), 10):
        chunk = records[i : i + 10]
        filtered = [_intersect_fields(r, schema) for r in chunk]
        attempt = 0
        merge_field = merge_field_id

        while attempt < max_retries:
            try:
                saved.extend(_perform_upsert(base_id, table_id, token, filtered, merge_field))
                break
            except RateLimitError:
                attempt += 1
                delay = max(backoff_seconds, backoff_seconds * attempt)
                logger.warning(f"Airtable 429 received; sleeping {delay}s before retry (attempt {attempt})")
                time.sleep(delay)
                continue
            except SchemaError as err:
                logger.warning(f"Airtable 422 on upsert; refreshing schema and retrying. {err}")
                schema = fetch_table_schema(base_id, table_id, token, force=True)
                filtered = [_intersect_fields(r, schema) for r in chunk]
                if merge_field == merge_field_id and fallback_field_id:
                    merge_field = fallback_field_id
                    continue
                attempt += 1
                continue
            except requests.RequestException as err:
                attempt += 1
                logger.error(f"Airtable upsert error attempt {attempt}: {err}")
                time.sleep(backoff_seconds)
                continue
        else:
            raise RuntimeError(f"Failed to upsert chunk after {max_retries} attempts")

    return saved
