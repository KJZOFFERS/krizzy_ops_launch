# src/common/airtable_client.py
import os
import httpx

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")


class AirtableClient:
    def __init__(self):
        if not AIRTABLE_API_KEY or not BASE_ID:
            raise RuntimeError("Missing Airtable env vars.")

        self.base_url = f"https://api.airtable.com/v0/{BASE_ID}"
        self.headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

    async def fetch(self, table, view=None):
        params = {}
        if view:
            params["view"] = view

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{self.base_url}/{table}",
                headers=self.headers,
                params=params
            )
            r.raise_for_status()
            return r.json().get("records", [])

    async def update(self, table, record_id, fields):
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.patch(
                f"{self.base_url}/{table}/{record_id}",
                headers=self.headers,
                json={"fields": fields}
            )
            r.raise_for_status()
            return r.json()

    async def create(self, table, fields):
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.base_url}/{table}",
                headers=self.headers,
                json={"fields": fields}
            )
            r.raise_for_status()
            return r.json()
