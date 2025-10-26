import asyncio, aiohttp
from utils.airtable_utils import write_record
from utils.discord_utils import post_ops
from utils.kpi import kpi_push

async def loop_rei():
    while True:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://api.publicapis.org/entries") as r:
                    if r.status == 200:
                        data = await r.json()
                        count = len(data.get("entries", []))
                        write_record("Leads_REI", {"Source": "ZillowFeed", "Count": count, "Status": "Active"})
                        await post_ops(f"🏘️ REI loop: {count} new leads")
                        kpi_push(event="rei_lead", data={"count": count})
        except Exception as e:
            await post_ops(f"REI loop error: {e}")
        await asyncio.sleep(900)
