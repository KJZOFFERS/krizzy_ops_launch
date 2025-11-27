# src/common/airtable_client.py

import json
import os
import re
import time
from typing import Any, Dict, Optional

import urllib.request
import urllib.error


AIRTABLE_API_BASE = "https://api.airtable.com/v0"
AIRTABLE_META_BASE = "https://api.airtable.com/v0/meta/bases"


def _http_request(url: str, api_key: str, method: str = "GET", body: Optional[dict] = None) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data: Optional[bytes] = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        # Raise with more context so logs are clear
        detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Airtable HTTPError {e.code} for {url}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Airtable URLError for {url}: {e}") from e


def _normalize_field_name(name: str) -> str:
    """
    Normalize a field key for matching:
    - lowercased
    - non-alphanumeric -> underscore
    - collapse multiple underscores
    """
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


class AirtableTable:
    """
    Table adapter with schema-aware safe writes.
    """

    def __init__(self, base_id: str, api_key: str, table_name: str, schema_fields: Dict[str, str]):
        """
        schema_fields: normalized_name -> actual_field_name
        """
        self.base_id = base_id
        self.api_key = api_key
        self.table_name = table_name
        self.schema_fields = schema_fields

    @property
    def _table_url(self) -> str:
        return f"{AIRTABLE_API_BASE}/{self.base_id}/{self.table_name}"

    def _filter_known_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Only send fields that exist in Airtable's current schema.
        This prevents 'Unknown field name "Service"' / 'Event Type' errors.
        """
        safe: Dict[str, Any] = {}
        for key, value in fields.items():
            norm = _normalize_field_name(key)
            actual = self.schema_fields.get(norm)
            if actual:
                safe[actual] = value
            # else: silently drop unknown fields
        return safe

    def create_record(self, fields: Dict[str, Any]) -> Optional[str]:
        safe_fields = self._filter_known_fields(fields)
        if not safe_fields:
            # Nothing valid to send; don't hit Airtable
            return None

        body = {"fields": safe_fields}
        resp = _http_request(self._table_url, self.api_key, method="POST", body=body)
        return resp.get("id")

    def update_record(self, record_id: str, fields: Dict[str, Any]) -> None:
        safe_fields = self._filter_known_fields(fields)
        if not safe_fields:
            return

        url = f"{self._table_url}/{record_id}"
        body = {"fields": safe_fields}
        _http_request(url, self.api_key, method="PATCH", body=body)


class AirtableClient:
    """
    Meta-schema-aware Airtable client.
    - Loads base schema once
    - get_table(name) returns a schema-safe AirtableTable
    """

    def __init__(self, base_id: str, api_key: str):
        self.base_id = base_id
        self.api_key = api_key
        self._schema_loaded_at: float = 0.0
        self._tables: Dict[str, Dict[str, str]] = {}  # table_name -> normalized_field -> actual_name

    @classmethod
    def from_env(cls) -> "AirtableClient":
        base_id = os.environ["AIRTABLE_BASE_ID"]
        api_key = os.environ["AIRTABLE_API_KEY"]
        return cls(base_id=base_id, api_key=api_key)

    def _load_schema(self, force: bool = False) -> None:
        now = time.time()
        # Refresh at most every 5 minutes unless forced
        if not force and self._schema_loaded_at and (now - self._schema_loaded_at) < 300:
            return

        url = f"{AIRTABLE_META_BASE}/{self.base_id}/tables"
        resp = _http_request(url, self.api_key, method="GET")

        tables: Dict[str, Dict[str, str]] = {}
        for table in resp.get("tables", []):
            table_name = table.get("name")
            field_map: Dict[str, str] = {}
            for field in table.get("fields", []):
                actual_name = field.get("name")
                norm_name = _normalize_field_name(actual_name)
                field_map[norm_name] = actual_name
            tables[table_name] = field_map

        self._tables = tables
        self._schema_loaded_at = now

    def get_table(self, table_name: str) -> AirtableTable:
        """
        Main entry used by engines:
            cracks = airtable.get_table("Cracks_Tracker")
            cracks.create_record({...})
        """
        self._load_schema()
        table_fields = self._tables.get(table_name)
        if table_fields is None:
            # Force reload once in case of new table, then re-check
            self._load_schema(force=True)
            table_fields = self._tables.get(table_name)
            if table_fields is None:
                # No table; use empty schema so writes become no-ops
                table_fields = {}

        return AirtableTable(
            base_id=self.base_id,
            api_key=self.api_key,
            table_name=table_name,
            schema_fields=table_fields,
        )

    # Optional helpers if you want one-liners elsewhere in the code:

    def log_crack(self, table_name: str, fields: Dict[str, Any]) -> None:
        """
        Example:
            client.log_crack("Cracks_Tracker", {
                "Engine": "REI",
                "Message": "Airtable write error",
                "Context": json.dumps(context),
            })
        """
        table = self.get_table(table_name)
        table.create_record(fields)

    def log_kpi(self, table_name: str, fields: Dict[str, Any]) -> None:
        """
        Example:
            client.log_kpi("KPI_Log", {
                "Engine": "REI",
                "Metric": "New Leads",
                "Value": 42,
            })
        """
        table = self.get_table(table_name)
        table.create_record(fields)
