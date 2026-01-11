import time
import requests
from typing import Dict, Any


class AirtableMetaCache:
    def __init__(self, pat: str, base_id: str, ttl_seconds: int = 900):
        self.pat = pat
        self.base_id = base_id
        self.ttl = ttl_seconds
        self._cache = None
        self._ts = 0

    def _headers(self):
        return {"Authorization": f"Bearer {self.pat}"}

    def fetch(self) -> Dict[str, Any]:
        now = time.time()
        if self._cache and (now - self._ts) < self.ttl:
            return self._cache

        url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables"
        r = requests.get(url, headers=self._headers(), timeout=20)
        r.raise_for_status()
        data = r.json()
        self._cache = data
        self._ts = now
        return data

    def invalidate(self):
        self._cache = None
        self._ts = 0

    def table_field_allowlist(self, table_id: str) -> Dict[str, str]:
        """Returns {field_name: field_id} for the table."""
        data = self.fetch()
        for t in data.get("tables", []):
            if t.get("id") == table_id:
                fields = t.get("fields", [])
                return {f["name"]: f["id"] for f in fields}
        raise ValueError(f"Table not found in Airtable meta schema: {table_id}")
