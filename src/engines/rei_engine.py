from src.common.airtable_client import get_airtable
from src.common.discord_notify import send_discord

async def run_rei_engine():
    airtable = get_airtable()
    if airtable is None:
        return {"error": "Airtable not configured"}

    records = await airtable.get("Leads_REI")
    await send_discord("REI Engine executed.")

    return records

