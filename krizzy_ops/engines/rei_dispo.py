import os, aiohttp, asyncio
from utils.airtable_utils import upsert
from utils.discord_utils import post_log, post_error
from utils.proxy_utils import get_proxy

URLS = [u.strip() for u in os.getenv("REI_FEED_URLS","").split(",") if u.strip()]
INTERVAL = int(os.getenv("REI_INTERVAL_SEC","3600"))

async def fetch(url, proxy):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, proxy=proxy, timeout=30) as r:
                if r.status!=200: await post_error(f"{url} {r.status}"); return []
                return (await r.json()).get("properties",[])
    except Exception as e: await post_error(f"{url}: {e}"); return []

async def loop_once():
    total=0
    for u in URLS:
        data = await fetch(u,get_proxy())
        for d in data:
            rec={"address":d.get("address"),"Ask":d.get("price")}
            await upsert("Leads_REI",rec,"address",rec["address"])
            total+=1
    await post_log(f"🟢 REI processed {total}")
    await asyncio.sleep(INTERVAL)
