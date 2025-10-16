import os, aiohttp, asyncio, urllib.parse as up
from utils.discord_utils import post_error

BASE=os.getenv("AIRTABLE_BASE_ID")
KEY=os.getenv("AIRTABLE_API_KEY")
HDR={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"}

async def _req(m,u,**kw):
    for i in range(5):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.request(m,u,headers=HDR,**kw) as r:
                    if r.status in (200,201): return await r.json()
                    if r.status in (429,500,502,503,504): await asyncio.sleep(2**i); continue
                    await post_error(f"Airtable {r.status}"); break
        except: await asyncio.sleep(2**i)
    return {}

async def upsert(tbl,f,uniq_field,uniq_val):
    enc=up.quote(f"{{{uniq_field}}}='{uniq_val}'")
    url=f"https://api.airtable.com/v0/{BASE}/{up.quote(tbl)}?filterByFormula={enc}"
    data=await _req("GET",url)
    if data.get("records"):
        rid=data["records"][0]["id"]
        return await _req("PATCH",f"https://api.airtable.com/v0/{BASE}/{up.quote(tbl)}/{rid}",json={"fields":f})
    return await _req("POST",f"https://api.airtable.com/v0/{BASE}/{up.quote(tbl)}",json={"fields":f})