import os, asyncio, json, requests, logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
app = FastAPI()

AIRTABLE_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE = os.getenv("AIRTABLE_BASE_ID")
OPS = os.getenv("DISCORD_OPS_WEBHOOK")
ERR = os.getenv("DISCORD_ERROR_WEBHOOK")

def headers():
    return {"Authorization": f"Bearer {AIRTABLE_KEY}", "Content-Type": "application/json"}

def discord(msg, error=False):
    url = ERR if error else OPS
    if url:
        try:
            requests.post(url, json={"content": msg}, timeout=10)
        except Exception as e:
            logging.error(f"Discord fail: {e}")

def airtable_push(table, record):
    try:
        r = requests.post(f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{table}",
                          headers=headers(), data=json.dumps({"fields": record}), timeout=10)
        if r.status_code >= 300:
            discord(f"Airtable push failed: {r.text}", True)
        else:
            logging.info(f"Pushed: {record.get('key', record.get('address', 'no key'))}")
    except Exception as e:
        discord(f"Airtable exception: {e}", True)

def fetch_airtable(table):
    try:
        r = requests.get(f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{table}", headers=headers(), timeout=10)
        r.raise_for_status()
        return r.json().get("records", [])
    except Exception as e:
        discord(f"Airtable fetch error {table}: {e}", True)
        return []

# ------------ ENGINES ------------------

async def lead_ingest_engine():
    os.makedirs("incoming_leads", exist_ok=True)
    while True:
        for f in os.listdir("incoming_leads"):
            if f.endswith(".json"):
                path = os.path.join("incoming_leads", f)
                try:
                    with open(path, "r") as file:
                        lead = json.load(file)
                    airtable_push("Leads_REI", lead)
                    os.remove(path)
                except Exception as e:
                    discord(f"Lead ingest file error {f}: {e}", True)
        await asyncio.sleep(60)

async def rei_dispo_engine():
    while True:
        leads = fetch_airtable("Leads_REI")
        for lead in leads:
            rec = lead.get("fields", {})
            if not rec: continue
            # simulate analysis
            result = {"Engine": "REI_DISPO", "LeadKey": rec.get("key", "unknown")}
            airtable_push("KPI_Log", result)
        discord("REI_DISPO_ENGINE cycle complete")
        await asyncio.sleep(300)

async def govcon_subtrap_engine():
    while True:
        opps = fetch_airtable("GovCon_Opportunities")
        for opp in opps:
            rec = opp.get("fields", {})
            if not rec: continue
            result = {"Engine": "GOVCON", "Opportunity": rec.get("Opportunity Name", "unknown")}
            airtable_push("KPI_Log", result)
        discord("GOVCON_SUBTRAP_ENGINE cycle complete")
        await asyncio.sleep(600)

async def watchdog():
    while True:
        discord("WATCHDOG: heartbeat ok")
        await asyncio.sleep(600)

# ------------ FASTAPI ------------------

@app.on_event("startup")
async def start():
    discord("KRIZZY OPS Enterprise v5 starting up...")
    asyncio.create_task(lead_ingest_engine())
    asyncio.create_task(rei_dispo_engine())
    asyncio.create_task(govcon_subtrap_engine())
    asyncio.create_task(watchdog())

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
