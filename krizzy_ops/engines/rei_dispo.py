import os, aiohttp, asyncio
from krizzy_ops.utils.airtable_utils import upsert
from krizzy_ops.utils.discord_utils import post_log, post_error
from krizzy_ops.utils.proxy_utils import get_proxy

URLS = [u.strip() for u in os.getenv("REI_FEED_URLS","").split(",") if u.strip()]
INTERVAL = int(os.getenv("REI_INTERVAL_SEC","3600"))

async def fetch(url, proxy):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, proxy=proxy, timeout=30) as r:
                if r.status!=200:
                    await post_error(f"{url} {r.status}")
                    return []
                return (await r.json()).get("properties",[])
    except Exception as e:
        await post_error(f"{url}: {e}")
        return []

async def loop_once():
    total=0
    for u in URLS:
        data = await fetch(u,get_proxy())
        for d in data:
            rec={"address":d.get("address"),"Ask":d.get("price")}
            if rec["address"]:
                await upsert("Leads_REI",rec,"address",rec["address"])
                total+=1
    await post_log(f"🟢 REI processed {total}")
    await asyncio.sleep(INTERVAL)
