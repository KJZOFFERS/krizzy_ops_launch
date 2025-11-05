import os, asyncio
import config_env_aliases  # normalize envs before anything else
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from config import CFG
from utils.discord_utils import post_ops, post_error
from utils import list_records, create_record
# Safe imports for background jobs
try:
    from ops_watchdog import heartbeat  # renamed to avoid clash with 3rd-party "watchdog"
except Exception:
    async def heartbeat():
        while True:
            try:
                post_ops("KRIZZY OPS heartbeat active")
            except Exception:
                pass
            await asyncio.sleep(60)

try:
    from worker import worker_loop
except Exception:
    async def worker_loop():
        while True:
            try:
                post_ops("KRIZZY OPS worker running...")
            except Exception:
                pass
            await asyncio.sleep(60)

APP_NAME = CFG.SERVICE_NAME
LEADS_TABLE = CFG.AIRTABLE_TABLE_LEADS
BUYERS_TABLE = CFG.AIRTABLE_TABLE_BUYERS

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "healthy", "service": APP_NAME}

@app.get("/ready")
def ready():
    return {"ready": True}

@app.get("/version")
def version():
    return {
        "service": APP_NAME,
        "commit": os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("GIT_SHA") or "unknown",
        "env": CFG.ENV
    }

# ---------- REI endpoints ----------
class Lead(BaseModel):
    key: str
    address: str
    Ask: Optional[float] = None
    Zip: Optional[str] = Field(None, description="5-digit")
    Beds: Optional[int] = None
    Baths: Optional[int] = None
    SqFt: Optional[int] = None
    Source_URL: Optional[str] = None

@app.post("/ingest/lead")
def ingest_lead(lead: Lead):
    try:
        exists = list_records(LEADS_TABLE, formula=f"{{key}} = '{lead.key}'", max_records=1)
        if exists:
            return {"status": "exists", "id": exists[0]["id"]}
        rec = create_record(LEADS_TABLE, lead.model_dump())
        return {"status": "created", "id": rec.get("id")}
    except Exception as e:
        post_error(f"/ingest/lead failed: {e}")
        raise

@app.post("/match/buyers/{lead_key}")
def match_buyers(lead_key: str):
    lr = list_records(LEADS_TABLE, formula=f"{{key}} = '{lead_key}'", max_records=1)
    if not lr:
        raise HTTPException(404, "lead not found")
    lead = lr[0]["fields"]
    ask = float(lead.get("Ask") or 0)
    zip5 = (lead.get("Zip") or "").strip()

    buyers = list_records(BUYERS_TABLE, formula="AND({opted_out} != 1)", max_records=1000)
    hits: List[Dict[str, Any]] = []
    for b in buyers:
        bf = b.get("fields", {})
        if zip5 and (bf.get("zip") or "").strip() != zip5:
            continue
