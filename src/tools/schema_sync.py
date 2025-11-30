# src/tools/schema_sync.py
import os
import json
import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/schema_sync")

BASE_ID = os.getenv("AIRTABLE_BASE_ID")
API_KEY = os.getenv("AIRTABLE_API_KEY")


@router.post("/")
async def sync_schema():
    if not BASE_ID or not API_KEY:
        raise HTTPException(500, "Missing Airtable env vars")

    url = f"https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables"

    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {API_KEY}"})
        r.raise_for_status()
        schema = r.json()

    with open("src/common/airtable_schema.json", "w") as f:
        json.dump(schema, f, indent=2)

    return {"status": "ok", "tables": len(schema.get("tables", []))}
