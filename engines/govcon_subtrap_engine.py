import asyncio, requests
from utils.airtable_utils import write_record
from utils.discord_utils import send_discord_message

async def run_govcon():
    try:
        resp = requests.get("https://api.sam.gov/opportunities/v1/search?limit=5")
        data = resp.json().get("opportunities", [])
        for opp in data:
            write_record("GovCon_Opportunities", opp)
        send_discord_message(f"GOVCON_SUBTRAP logged {len(data)} opportunities")
    except Exception as e:
        send_discord_message(f"GOVCON_SUBTRAP error: {e}", "errors")
        await asyncio.sleep(60)
