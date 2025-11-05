import asyncio, logging
from utils.discord_utils import post_ops, post_error
from utils.airtable_utils import fetch_table, safe_airtable_write

async def loop_govcon():
    while True:
        try:
            post_ops("GOVCON_SUBTRAP_ENGINE: polling new opportunities...")
            opps = fetch_table("GovCon_Opportunities")
            for opp in opps:
                record = opp.get("fields", {})
                if record:
                    safe_airtable_write("KPI_Log", {"Engine": "GovCon", "Opportunity": record.get("Opportunity Name")})
            await asyncio.sleep(600)
        except Exception as e:
            post_error(f"GOVCON_SUBTRAP_ENGINE loop error: {e}")
            await asyncio.sleep(60)
