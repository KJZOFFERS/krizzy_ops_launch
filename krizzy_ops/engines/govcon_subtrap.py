import os, aiohttp, asyncio, urllib.parse as up
from utils.airtable_utils import upsert
from utils.discord_utils import post_log, post_error
from utils.proxy_utils import get_proxy

SAM_KEY=os.getenv("SAM_API_KEY","")
NAICS=[n.strip() for n in os.getenv("NAICS_WHITELIST","").split(",") if n.strip()]
INTERVAL=int(os.getenv("GOVCON_INTERVAL_SEC","3600"))
BASE="https://api.sam.gov/prod/opportunities/v2/search"

async def pull():
    if not SAM_KEY: return []
    q={"api_key":SAM_KEY,"limit":"25","noticeType":"Combined Synopsis/Solicitation","sort":"-publishedOn"}
    if NAICS: q["naics"]=",".join(NAICS)
    url=f"{BASE}?{up.urlencode(q)}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url,proxy=get_proxy(),timeout=40) as r:
                if r.status!=200: await post_error(f"SAM {r.status}"); return []
                return (await r.json()).get("opportunitiesData",[])
    except Exception as e: await post_error(f"SAM: {e}"); return []

async def loop_once():
    items=await pull(); c=0
    for i in items:
        f={"Opportunity Name":i.get("title"),"Agency":i.get("organizationName"),
           "Total Value":i.get("awardAmount"),"NAICS Code":",".join(i.get("naicsCodes",[])),
           "Submission Deadline":i.get("responseDeadLine"),"Link":i.get("uiLink")}
        if f["Opportunity Name"]:
            await upsert("GovCon Opportunities",f,"Link",f["Link"])
            c+=1
    await post_log(f"🟢 GovCon upserted {c}")
    await asyncio.sleep(INTERVAL)