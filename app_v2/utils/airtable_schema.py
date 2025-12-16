"""
Airtable Schema Guard - fetches and caches table schemas to prevent 422 errors.
"""
import requests
import time
from typing import Dict, Any, Set

_schema_cache: Dict[str, Set[str]] = {}
_cache_timestamp: float = 0.0
CACHE_TTL_SECONDS = 300


def fetch_schema(base_id: str, api_key: str, force_refresh: bool = False) -> Dict[str, Set[str]]:
    """Fetch table schemas from Airtable Meta API."""
    global _schema_cache, _cache_timestamp

    now = time.time()
    if not force_refresh and _schema_cache and (now - _cache_timestamp) < CACHE_TTL_SECONDS:
        return _schema_cache

    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()
    new_cache: Dict[str, Set[str]] = {}

    for table in data.get("tables", []):
        table_name = table.get("name", "")
        fields = table.get("fields", [])
        new_cache[table_name] = {f.get("name") for f in fields if f.get("name")}

    _schema_cache = new_cache
    _cache_timestamp = now
    return _schema_cache


def refresh_schema(base_id: str, api_key: str) -> Dict[str, Set[str]]:
    """Force refresh the schema cache."""
    return fetch_schema(base_id, api_key, force_refresh=True)


def filter_fields(fields: Dict[str, Any], table: str, base_id: str, api_key: str) -> Dict[str, Any]:
    """Filter fields to only include valid schema fields with non-None values."""
    schema = fetch_schema(base_id, api_key)
    allowed = schema.get(table, set())

    return {k: v for k, v in fields.items() if v is not None and (not allowed or k in allowed)}
