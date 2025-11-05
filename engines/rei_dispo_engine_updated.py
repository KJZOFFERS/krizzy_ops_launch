import asyncio, logging
from utils.discord_utils import post_ops, post_error
from utils.airtable_utils import fetch_table, safe_airtable_write

async def loop_rei():
    while True:
        try:
            post_ops("REI_DISPO_ENGINE: polling new leads...")
            leads = fetch_table("Leads_REI")
            for lead in leads:
                record = lead.get("fields", {})
                if record:
                    safe_airtable_write("KPI_Log", {"Engine": "REI", "LeadKey": record.get("key")})
            await asyncio.sleep(300)
        except Exception as e:
            post_error(f"REI_DISPO_ENGINE loop error: {e}")
            await asyncio.sleep(60)

