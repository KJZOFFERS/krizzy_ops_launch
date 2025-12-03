import httpx
import os

class AirtableClient:
    def __init__(self):
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.api_key = os.getenv("AIRTABLE_API_KEY")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        self.client = httpx.AsyncClient(timeout=30.0)

    async def get(self, table):
        url = f"https://api.airtable.com/v0/{self.base_id}/{table}"
        r = await self.client.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()

    async def update(self, table, record_id, fields):
        url = f"https://api.airtable.com/v0/{self.base_id}/{table}/{record_id}"
        payload = {"fields": fields}
        r = await self.client.patch(url, headers=self.headers, json=payload)
        r.raise_for_status()
        return r.json()

        return AirtableClient()
    except Exception:
        return None
