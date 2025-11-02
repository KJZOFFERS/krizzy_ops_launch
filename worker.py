import os
import time
import requests
import aiohttp
import asyncio

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS")

SAM_API_KEY = os.getenv("SAM_API_KEY")
NAICS_WHITELIST = [x.strip() for x in os.getenv("NAICS_WHITELIST", "").split(",")]

TABLE_LEADS = "Leads_REI"
TABLE_BUYERS = "Buyers"
TABLE_GOVCON = "GovCon_Opportunities"
TABLE_KPI = "KPI_Log"

def notify(msg):
    if WEBHOOK_OPS:
        try:
            requests.post(WEBHOOK_OPS, json={"content": msg}, timeout=8)
        except:
            pass

async def airtable_list(table):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers) as r:
            return (await r.json()).get("records", [])

async def airtable_upsert(table, fields):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as s:
        await s.post(url, headers=headers, json={"fields": fields})

async def rei_cycle():
    leads = await airtable_list(TABLE_LEADS)
    buyers = await airtable_list(TABLE_BUYERS)

    for lead in leads:
        lf = lead["fields"]
        lead_city = lf.get("City")
        lead_state = lf.get("State")
        lead_price = lf.get("Price")

        for buyer in buyers:
            bf = buyer["fields"]
            if bf.get("State") == lead_state:
                notify(f"[REI MATCH] {lf.get('Address')} → {bf.get('Buyer_Name')}")
                break

    await airtable_upsert(TABLE_KPI, {"cycle": "rei", "timestamp": int(time.time())})
    notify("[REI] cycle complete")

async def govcon_cycle():
    url = "https://api.sam.gov/prod/opportunities/v2/search"
    params = {
        "api_key": SAM_API_KEY,
        "limit": 10
    }
    async with aiohttp.ClientSession() as s:
        async with s.get(url, params=params) as r:
            data = await r.json()

    for opp in data.get("opportunitiesData", []):
        if str(opp.get("naicsCode")) in NAICS_WHITELIST:
            await airtable_upsert(TABLE_GOVCON, {
                "Solicitation": opp.get("title"),
                "NAICS": opp.get("naicsCode"),
                "Agency": opp.get("agency"),
                "DueDate": opp.get("responseDate")
            })
            notify(f"[GOVCON] {opp.get('title')}")

    await airtable_upsert(TABLE_KPI, {"cycle": "govcon", "timestamp": int(time.time())})
    notify("[GOVCON] cycle complete")

async def run_loop():
    while True:
        await rei_cycle()
        await govcon_cycle()
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(run_loop())
