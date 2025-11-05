import os, aiohttp, asyncio, urllib.parse as up
from utils.discord_utils import post_error

BASE = os.getenv("AIRTABLE_BASE_ID")
KEY = os.getenv("AIRTABLE_API_KEY")
HDR = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


async def _req(method: str, url: str, **kw):
    # Basic guard if KEY or BASE missing to avoid hammering
    if not KEY or not BASE:
        await post_error("Airtable keys/base not configured")
        return {}
    for i in range(5):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.request(method, url, headers=HDR, **kw) as r:
                    if r.status in (200, 201):
                        return await r.json()
                    if r.status in (429, 500, 502, 503, 504):
                        await asyncio.sleep(2 ** i)
                        continue
                    await post_error(f"Airtable {r.status}")
                    break
        except Exception:
            await asyncio.sleep(2 ** i)
    return {}


async def upsert(table: str, fields: dict, unique_field: str, unique_value: str):
    enc = up.quote(f"{{{unique_field}}}='{unique_value}'")
    url = f"https://api.airtable.com/v0/{BASE}/{up.quote(table)}?filterByFormula={enc}"
    data = await _req("GET", url)
    if data.get("records"):
        record_id = data["records"][0]["id"]
        return await _req(
            "PATCH",
            f"https://api.airtable.com/v0/{BASE}/{up.quote(table)}/{record_id}",
            json={"fields": fields},
        )
    return await _req(
        "POST",
        f"https://api.airtable.com/v0/{BASE}/{up.quote(table)}",
        json={"fields": fields},
    )
