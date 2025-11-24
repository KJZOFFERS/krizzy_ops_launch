"""
Airtable client using REST + Meta API only.
No pyairtable, no TableSchema, schema is handled as plain dicts.
"""

import os
import time
import json
from typing import Any, Dict, List, Optional

import requests


AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")

if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
    print("[AIRTABLE] WARNING: AIRTABLE_API_KEY or AIRTABLE_BASE_ID not set")


class AirtableSchemaError(Exception):
    pass


def _airtable_request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Low-level Airtable HTTP helper.
    path is either:
      - f"/{AIRTABLE_BASE_ID}/{table_name}" for records
      - f"/meta/bases/{AIRTABLE_BASE_ID}/tables" for schema
    """
    base_url = "https://api.airtable.com/v0"
    url = base_url + path

    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.request(method, url, headers=headers, params=params, json=payload, timeout=30)
    if not resp.ok:
        raise AirtableSchemaError(
            f"Airtable HTTP {resp.status_code}: {resp.text[:500]}"
        )
    data = resp.json()
    if not isinstance(data, dict):
        raise AirtableSchemaError(f"Unexpected Airtable response type: {type(data)}")
    return data


def _list_records(
    table_name: str,
    max_records: int = 100,
    filter_by_formula: Optional[str] = None,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"maxRecords": max_records}
    if filter_by_formula:
        params["filterByFormula"] = filter_by_formula
    data = _airtable_request(
        "GET",
        f"/{AIRTABLE_BASE_ID}/{table_name}",
        params=params,
    )
    return data.get("records", [])


def _create_records(
    table_name: str,
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    payload = {"records": records}
    data = _airtable_request(
        "POST",
        f"/{AIRTABLE_BASE_ID}/{table_name}",
        payload=payload,
    )
    return data.get("records", [])


def _update_records(
    table_name: str,
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    payload = {"records": records}
    data = _airtable_request(
        "PATCH",
        f"/{AIRTABLE_BASE_ID}/{table_name}",
        payload=payload,
    )
    return data.get("records", [])


class AirtableClient:
    """
    Schema-aware Airtable client that:
      - Fetches schema via Meta API
      - Caches schema
      - Filters fields before write
      - Provides safe_create / safe_update / safe_upsert
      - Provides log_kpi / log_crack helpers
    """

    def __init__(self) -> None:
        if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
            raise AirtableSchemaError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID are required")
        self._schema_cache: Dict[str, tuple] = {}
        self._schema_ttl_sec = 60 * 30  # 30 minutes

    # ---------- Schema helpers ----------

    def _fetch_tables_schema(self) -> List[Dict[str, Any]]:
        data = _airtable_request(
            "GET",
            f"/meta/bases/{AIRTABLE_BASE_ID}/tables",
            params={"include": "visibleFieldIds"},
        )
        return data.get("tables", [])

    def schema(self, table_name: str, force: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force and table_name in self._schema_cache:
            ts, sch = self._schema_cache[table_name]
            if now - ts < self._schema_ttl_sec:
                return sch

        tables = self._fetch_tables_schema()
        for t in tables:
            if t.get("name") == table_name:
                self._schema_cache[table_name] = (now, t)
                return t

        raise AirtableSchemaError(f"Table '{table_name}' not found in Meta API schema")

    def allowed_fields(self, table_name: str) -> List[str]:
        sch = self.schema(table_name)
        fields = sch.get("fields", []) or []
        return [f.get("name") for f in fields if f.get("name")]

    def filter_record(self, table_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
        allowed = set(self.allowed_fields(table_name))
        return {k: v for k, v in record.items() if k in allowed}

    # ---------- CRUD helpers ----------

    def safe_create(self, table_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
        filtered = self.filter_record(table_name, record)
        if not filtered:
            raise AirtableSchemaError(
                f"No fields matched schema for {table_name}. keys={list(record.keys())}"
            )
        created = _create_records(table_name, [{"fields": filtered}])
        if not created:
            raise AirtableSchemaError(f"Create failed for {table_name}")
        return created[0]

    def safe_update(self, table_name: str, record_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        filtered = self.filter_record(table_name, updates)
        if not filtered:
            raise AirtableSchemaError(
                f"No update fields matched schema for {table_name}. keys={list(updates.keys())}"
            )
        updated = _update_records(table_name, [{"id": record_id, "fields": filtered}])
        if not updated:
            raise AirtableSchemaError(f"Update failed for {table_name}")
        return updated[0]

    def safe_upsert(
        self,
        table_name: str,
        record: Dict[str, Any],
        match_fields: List[str],
    ) -> Dict[str, Any]:
        filtered = self.filter_record(table_name, record)
        if not filtered:
            raise AirtableSchemaError(
                f"No fields matched schema for {table_name}. keys={list(record.keys())}"
            )

        allowed = set(self.allowed_fields(table_name))
        usable_match_fields = [
            f for f in match_fields
            if f in allowed and f in filtered and filtered[f]
        ]

        # Try update path
        if usable_match_fields:
            mf = usable_match_fields[0]
            mv = filtered[mf]
            formula = f"{{{mf}}}='{mv}'"
            found = _list_records(table_name, max_records=1, filter_by_formula=formula)
            if found:
                rec_id = found[0]["id"]
                updated = _update_records(table_name, [{"id": rec_id, "fields": filtered}])
                return {
                    "action": "updated",
                    "record": updated[0] if updated else found[0],
                    "match_field": mf,
                }

        # Create path
        created = _create_records(table_name, [{"fields": filtered}])
        return {
            "action": "created",
            "record": created[0] if created else {},
            "match_field": usable_match_fields[0] if usable_match_fields else None,
        }

    # ---------- Read helpers ----------

    def list_records(
        self,
        table_name: str,
        max_records: int = 100,
        filter_by_formula: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return _list_records(table_name, max_records=max_records, filter_by_formula=filter_by_formula)

    # ---------- Logging helpers ----------

    def log_kpi(self, event: str, data: Dict[str, Any]) -> None:
        payload = {
            "Event": event,
            "Data": json.dumps(data, ensure_ascii=False),
            "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            self.safe_create("KPI_Log", payload)
        except Exception as e:
            print(f"[KPI_LOG] Failed: {e}")

    def log_crack(self, source: str, error: str, data: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "Source": source,
            "Error": error[:5000],
            "Data": json.dumps(data or {}, ensure_ascii=False),
            "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "Status": "open",
        }
        try:
            self.safe_create("Cracks_Tracker", payload)
        except Exception as e:
            print(f"[CRACK_LOG] Failed: {e}")
