import os
import httpx


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

    async def get(self, table: str):
        url = f"https://api.airtable.com/v0/{self.base_id}/{table}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def create(self, table: str, fields: dict):
        url = f"https://api.airtable.com/v0/{self.base_id}/{table}"
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json={"fields": fields}, headers=self.headers)
            r.raise_for_status()
            return r.json()


def get_airtable():
    """
    Lazy-loaded Airtable client. Returns None if misconfigured.
    Keeps container stable even with missing env vars.
    """
    try:
        return AirtableClient()
    except Exception:
        return None
