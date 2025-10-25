import asyncio, requests, os
from utils.airtable_utils import write_record
from utils.discord_utils import send_discord_message

async def run_rei_dispo():
    try:
        resp = requests.get("https://api.biggerpockets.com/deals")
        data = resp.json()[:10]
        for deal in data:
            write_record("Leads_REI", deal)
        send_discord_message(f"REI_DISPO imported {len(data)} deals")
    except Exception as e:
        send_discord_message(f"REI_DISPO error: {e}", "errors")
        await asyncio.sleep(60)
