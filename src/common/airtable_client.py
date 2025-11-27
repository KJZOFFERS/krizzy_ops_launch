 # src/common/airtable_client.py

import os
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import requests


class AirtableError(Exception):
    """Custom error for Airtable API failures."""


class AirtableSchemaError(AirtableError):
    """Raised when schema validation fails."""


class AirtableClient:
    """
    Thin wrapper around Airtable REST + Meta API.

    Uses:
      - AIRTABLE_API_KEY
      - AIRTABLE_BASE_ID

    Endpoints:
      - Meta (schema): https://api.airtable.com/v0/meta/bases/{base_id}/tables
      - Records:       https://api.airtable.com/v0/{base_id}/{table_name}
    """

    META_URL_TEMPLATE = "https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    RECORDS_URL_TEMPLATE = "https://api.airtable.com/v0/{base_id}/{table_name}"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_id: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.getenv("AIRTABLE_API_KEY", "").strip()
        self.base_id = base_id or os.getenv("AIRTABLE_BASE_ID", "").strip()
        self.timeout = timeout
        self.max_retries = max_retries

        if not self.api_key:
            raise AirtableError("AIRTABLE_API_KEY is not set")

        if not self.base_id:
            raise AirtableError("AIRTABLE_BASE_ID is not set")

        if self.base_id.startswith("http"):
            raise AirtableError(
                "AIRTABLE_BASE_ID must be a base id (e.g. 'appIe21nS9Z9ahV7V'), "
                "not an Airtable URL."
            )

        self._tables_cache: Optional[List[Dict[str, Any]]] = None

    @property
    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.request(
                    method=method.upper(),
                    url=url,
                    headers=self._auth_headers,
                    params=params,
                    json=json,
                    timeout=self.timeout,
                )
                if resp.status_code == 429 and attempt < self.max_retries:
                    retry_after = int(resp.headers.get("Retry-After", "1"))
                    time.sleep(retry_after or attempt)
                    continue

                if not resp.ok:
                    raise AirtableError(
                        f"Airtable {method} {url} failed "
                        f"({resp.status_code}): {resp.text}"
                    )

                data = resp.json()
                if not isinstance(data, dict):
                    raise AirtableError(
                        f"Unexpected Airtable response format for {method} {url}"
                    )
                return data

            except Exception as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    raise
                time.sleep(attempt)

        if last_exc:
            raise last_exc
        raise AirtableError("Unknown Airtable request failure")

    def refresh_tables_cache(self) -> List[Dict[str, Any]]:
        url = self.META_URL_TEMPLATE.format(base_id=self.base_id)
        data = self._request("GET", url)
        tables = data.get("tables", [])
        if not isinstance(tables, list):
            raise AirtableError("Invalid Meta API payload: 'tables' is not a list")
        self._tables_cache = tables
        return tables

    def get_tables(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        if use_cache and self._tables_cache is not None:
            return self._tables_cache
        return self.refresh_tables_cache()

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        tables = self.get_tables()
        for tbl in tables:
            if tbl.get("name") == table_name:
                return tbl
        raise AirtableSchemaError(f"Table '{table_name}' not found in Meta API")

    def get_field_names(self, table_name: str) -> List[str]:
        schema = self.get_table_schema(table_name)
        fields = schema.get("fields", [])
        return [f.get("name") for f in fields if isinstance(f, dict)]

    def list_records(
        self,
        table_name: str,
        *,
        view: Optional[str] = None,
        filter_formula: Optional[str] = None,
        fields: Optional[List[str]] = None,
        max_records: Optional[int] = None,
        page_size: int = 100,
        sort: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        url = self.RECORDS_URL_TEMPLATE.format(
            base_id=self.base_id, table_name=table_name
        )

        params: Dict[str, Any] = {"pageSize": page_size}

        if view:
            params["view"] = view
        if filter_formula:
            params["filterByFormula"] = filter_formula
        if fields:
            for idx, f_name in enumerate(fields):
                params[f"fields[{idx}]"] = f_name
        if sort:
            for idx, s in enumerate(sort):
                params[f"sort[{idx}][field]"] = s.get("field", "")
                params[f"sort[{idx}][direction]"] = s.get("direction", "asc")

        all_records: List[Dict[str, Any]] = []
        offset: Optional[str] = None

        while True:
            if offset:
                params["offset"] = offset

            data = self._request("GET", url, params=params)
            records = data.get("records", [])
            if not isinstance(records, list):
                raise AirtableError("Invalid records payload (no 'records' list)")

            all_records.extend(records)

            if max_records and len(all_records) >= max_records:
                return all_records[:max_records]

            offset = data.get("offset")
            if not offset:
                break

        return all_records

    def create_record(self, table_name: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        url = self.RECORDS_URL_TEMPLATE.format(
            base_id=self.base_id, table_name=table_name
        )
        payload = {"fields": fields}
        return self._request("POST", url, json=payload)

    def update_record(
        self,
        table_name: str,
        record_id: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = self.RECORDS_URL_TEMPLATE.format(
            base_id=self.base_id, table_name=table_name
        )
        payload = {
            "records": [
                {
                    "id": record_id,
                    "fields": fields,
                }
            ]
        }
        return self._request("PATCH", url, json=payload)

    def delete_record(self, table_name: str, record_id: str) -> Dict[str, Any]:
        url = self.RECORDS_URL_TEMPLATE.format(
            base_id=self.base_id, table_name=table_name
        )
        params = {"records[]": record_id}
        return self._request("DELETE", url, params=params)

    def find_first_by_formula(
        self,
        table_name: str,
        filter_formula: str,
        *,
        view: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        records = self.list_records(
            table_name,
            filter_formula=filter_formula,
            view=view,
            fields=fields,
            max_records=1,
        )
        return records[0] if records else None

    def safe_upsert(
        self,
        table_name: str,
        fields: Dict[str, Any],
        match_fields: List[str],
        typecast: bool = False,
    ) -> Dict[str, Any]:
        """
        Upsert by checking existence based on match_fields.
        Returns: {"action": "created" | "updated", "record": {...}}
        """
        conditions = []
        for field_name in match_fields:
            value = fields.get(field_name)
            if value is None:
                continue
            value_str = str(value).replace('"', '\\"')
            conditions.append(f"{{{field_name}}} = \"{value_str}\"")

        if not conditions:
            rec = self.create_record(table_name, fields)
            return {"action": "created", "record": rec}

        formula = "AND(" + ", ".join(conditions) + ")"
        existing = self.find_first_by_formula(table_name, formula)

        if existing:
            rec_id = existing["id"]
            rec = self.update_record(table_name, rec_id, fields)
            return {"action": "updated", "record": rec}
        else:
            rec = self.create_record(table_name, fields)
            return {"action": "created", "record": rec}

    def ping(self) -> bool:
        """Lightweight health-check: confirms that Meta API and auth work."""
        try:
            self.get_tables(use_cache=False)
            return True
        except Exception:
            return False

    def log_kpi(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log KPI event to KPI_Log table"""
        try:
            self.create_record(
                "KPI_Log",
                {
                    "Event Type": event_type,
                    "Data": str(data)[:10000],
                    "Timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as e:
            print(f"[AIRTABLE] Failed to log KPI: {e}")

    def log_crack(self, service: str, error: str) -> None:
        """Log crack/error to Cracks_Tracker table"""
        try:
            self.create_record(
                "Cracks_Tracker",
                {
                    "Service": service,
                    "Error": error[:10000],
                    "Timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as e:
            print(f"[AIRTABLE] Failed to log crack: {e}")
