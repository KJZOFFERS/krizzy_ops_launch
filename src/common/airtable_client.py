# src/common/airtable_client.py
# Airtable client with get, create, and update methods

import os
import httpx
from typing import Optional, List, Dict, Any


class AirtableClient:
    def __init__(self):
        self.token = os.getenv("AIRTABLE_API_KEY")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")

        if not self.token or not self.base_id:
            raise RuntimeError("Missing Airtable env vars.")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.timeout = 30.0

    async def get(self, table: str, filter_formula: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch records from a table. Returns raw Airtable response with 'records' key.
        Supports optional filterByFormula.
        """
        url = f"https://api.airtable.com/v0/{self.base_id}/{table}"
        params = {}
        if filter_formula:
            params["filterByFormula"] = filter_formula

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(url, headers=self.headers, params=params)
            r.raise_for_status()
            return r.json()

    async def get_all(self, table: str, filter_formula: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch all records (handles pagination). Returns list of records.
        """
        url = f"https://api.airtable.com/v0/{self.base_id}/{table}"
        params: Dict[str, Any] = {}
        if filter_formula:
            params["filterByFormula"] = filter_formula

        all_records: List[Dict[str, Any]] = []
        offset: Optional[str] = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                if offset:
                    params["offset"] = offset
                r = await client.get(url, headers=self.headers, params=params)
                r.raise_for_status()
                data = r.json()
                all_records.extend(data.get("records", []))
                offset = data.get("offset")
                if not offset:
                    break

        return all_records

    async def create(self, table: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a single record.
        """
        url = f"https://api.airtable.com/v0/{self.base_id}/{table}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, json={"fields": fields}, headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def update(self, table: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a single record by ID (PATCH = partial update).
        """
        url = f"https://api.airtable.com/v0/{self.base_id}/{table}/{record_id}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.patch(url, json={"fields": fields}, headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def batch_update(self, table: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Batch update up to 10 records at a time.
        records = [{"id": "recXXX", "fields": {...}}, ...]
        """
        url = f"https://api.airtable.com/v0/{self.base_id}/{table}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.patch(url, json={"records": records}, headers=self.headers)
            r.raise_for_status()
            return r.json()


def get_airtable() -> Optional[AirtableClient]:
    """
    Lazy-loaded Airtable client. Returns None if misconfigured.
    Keeps container stable even with missing env vars.
    """
    try:
        return AirtableClient()
    except Exception:
        return None
