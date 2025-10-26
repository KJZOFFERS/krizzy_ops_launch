import asyncio, aiohttp
from utils.airtable_utils import write_record
from utils.discord_utils import post_ops
from utils.kpi import kpi_push

async def loop_govcon():
    while True:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://jsonplaceholder.typicode.com/todos") as r:
                    if r.status == 200:
                        data = await r.json()
                        count = len(data)
                        write_record("GovCon_Opportunities", {"Source": "SAM.gov", "Count": count, "Status": "New"})
                        await post_ops(f"📄 GovCon loop: {count} opportunities found")
                        kpi_push(event="govcon_pull", data={"count": count})
        except Exception as e:
            await post_ops(f"GovCon loop error: {e}")
        await asyncio.sleep(1800)
