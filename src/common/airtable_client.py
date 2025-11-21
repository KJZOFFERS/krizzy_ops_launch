import os
import time
import json
from typing import Any, Dict, List, Optional, Tuple

from pyairtable import Api
from pyairtable.api.table import Table


class AirtableSchemaError(Exception):
    pass


class AirtableClient:
    """
    Schema-locked safe Airtable client:
      - Uses Meta API via table.schema() (returns dict)
      - Filters payload to existing fields only
      - Upserts using first available match field from candidates
    """

    def __init__(self):
        api_key = os.getenv("AIRTABLE_API_KEY", "")
        base_id = os.getenv("AIRTABLE_BASE_ID", "")
        if not api_key or not base_id:
            raise AirtableSchemaError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID are required")

        self.api = Api(api_key)
        self.base_id = base_id
        self._schema_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._schema_ttl_sec = 60 * 30  # 30 min

    def get_table(self, table_name: str) -> Table:
        return self.api.table(self.base_id, table_name)

    def schema(self, table_name: str, force: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force and table_name in self._schema_cache:
            ts, sch = self._schema_cache[table_name]
            if now - ts < self._schema_ttl_sec:
                return sch

        table = self.get_table(table_name)
        sch = table.schema()  # dict
        self._schema_cache[table_name] = (now, sch)
        return sch

    def allowed_fields(self, table_name: str) -> List[str]:
        sch = self.schema(table_name)
        fields = sch.get("fields", []) or []
        return [f.get("name") for f in fields if f.get("name")]

    def filter_record(self, table_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
        allowed = set(self.allowed_fields(table_name))
        return {k: v for k, v in record.items() if k in allowed}

    def safe_create(self, table_name: str, record: Dict[str, Any], typecast: bool = False) -> Dict[str, Any]:
        table = self.get_table(table_name)
        filtered = self.filter_record(table_name, record)
        if not filtered:
            raise AirtableSchemaError(
                f"No fields matched schema for {table_name}. keys={list(record.keys())}"
            )
        return table.create(filtered, typecast=typecast)

    def safe_update(self, table_name: str, record_id: str, updates: Dict[str, Any], typecast: bool = False) -> Dict[str, Any]:
        table = self.get_table(table_name)
        filtered = self.filter_record(table_name, updates)
        if not filtered:
            raise AirtableSchemaError(
                f"No update fields matched schema for {table_name}. keys={list(updates.keys())}"
            )
        return table.update(record_id, filtered, typecast=typecast)

    def safe_upsert(
        self,
        table_name: str,
        record: Dict[str, Any],
        match_fields: List[str],
        typecast: bool = False,
    ) -> Dict[str, Any]:
        """
        Upsert using the FIRST match field that exists in schema AND is present in filtered record.
        If none exist, falls back to create (still schema-safe).
        """
        table = self.get_table(table_name)
        filtered = self.filter_record(table_name, record)
        if not filtered:
            raise AirtableSchemaError(
                f"No fields matched schema for {table_name}. keys={list(record.keys())}"
            )

        allowed = set(self.allowed_fields(table_name))
        usable_match_fields = [f for f in match_fields if f in allowed and f in filtered and filtered[f]]

        if usable_match_fields:
            mf = usable_match_fields[0]
            mv = filtered[mf]
            formula = f"{{{mf}}}='{mv}'"
            found = table.all(formula=formula, max_records=1)
            if found:
                rec_id = found[0]["id"]
                updated = table.update(rec_id, filtered, typecast=typecast)
                return {"action": "updated", "record": updated, "match_field": mf}
            created = table.create(filtered, typecast=typecast)
            return {"action": "created", "record": created, "match_field": mf}

        created = table.create(filtered, typecast=typecast)
        return {"action": "created", "record": created, "match_field": None}

    # Logging helpers (schema-safe, but drop fields if not present)
    def log_kpi(self, event: str, data: Dict[str, Any]) -> None:
        payload = {
            "Event": event,
            "Data": json.dumps(data, ensure_ascii=False),
            "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.safe_create("KPI_Log", payload, typecast=False)

    def log_crack(self, source: str, error: str, data: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "Source": source,
            "Error": error[:5000],
            "Data": json.dumps(data or {}, ensure_ascii=False),
            "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "Status": "open",
        }
        self.safe_create("Cracks_Tracker", payload, typecast=False)
