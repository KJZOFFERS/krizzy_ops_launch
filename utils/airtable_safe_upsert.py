import requests
from typing import Dict, Any, List, Tuple
from utils.airtable_meta import AirtableMetaCache


class AirtableSafeUpsert:
    def __init__(self, pat: str, base_id: str, meta: AirtableMetaCache):
        self.pat = pat
        self.base_id = base_id
        self.meta = meta

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
        }

    def _intersect_fields(self, table_id: str, fields: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        allow = self.meta.table_field_allowlist(table_id)  # name -> id
        kept = {}
        dropped = []
        for k, v in fields.items():
            if k in allow:
                kept[k] = v
            else:
                dropped.append(k)
        return kept, dropped

    def upsert(
        self,
        table_id: str,
        records: List[Dict[str, Any]],
        merge_field_id: str,
    ) -> Dict[str, Any]:
        """
        Uses Airtable upsert with fieldIdsToMergeOn (requires field ID).
        We write with FIELD NAMES (not IDs) but intersect to avoid 422.
        """
        url = f"https://api.airtable.com/v0/{self.base_id}/{table_id}"
        safe_records = []
        dropped_all = []

        for rec in records:
            fields = rec.get("fields", {})
            safe_fields, dropped = self._intersect_fields(table_id, fields)
            dropped_all.append({"dropped": dropped})
            safe_records.append({"fields": safe_fields})

        payload = {
            "records": safe_records,
            "performUpsert": {
                "fieldsToMergeOn": [merge_field_id]  # Airtable expects field IDs here
            },
        }

        r = requests.patch(url, headers=self._headers(), json=payload, timeout=30)
        if r.status_code == 422:
            # Schema drift: refresh and retry once
            self.meta.invalidate()
            allow_retry = []
            for rec in records:
                safe_fields, _ = self._intersect_fields(table_id, rec.get("fields", {}))
                allow_retry.append({"fields": safe_fields})
            payload["records"] = allow_retry
            r2 = requests.patch(url, headers=self._headers(), json=payload, timeout=30)
            if r2.status_code == 422:
                return {
                    "ok": False,
                    "error": "AIRTABLE_422_SCHEMA_GUARD_FAIL",
                    "status": r2.status_code,
                    "body": r2.text[:2000],
                    "dropped": dropped_all,
                }
            r2.raise_for_status()
            return {"ok": True, "data": r2.json(), "dropped": dropped_all}

        r.raise_for_status()
        return {"ok": True, "data": r.json(), "dropped": dropped_all}
