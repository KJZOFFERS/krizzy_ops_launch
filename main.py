# FILE: main.py
import os, asyncio
import config_env_aliases  # normalize env before anything else
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from config import CFG
from utils.discord_utils import post_ops, post_error
from utils import list_records, create_record
from utils.watchdog import heartbeat          # <- correct path
from worker import worker_loop

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
        try:
            if ask and float(bf.get("budget_max", 0) or 0) < ask:
                continue
        except Exception:
            continue
        hits.append({
            "buyer_id": b["id"],
            "phone": bf.get("phone"),
            "strategy": bf.get("strategy"),
            "budget_max": bf.get("budget_max"),
        })
    return {"lead_key": lead_key, "matches": hits[:10]}

# ---------- background tasks ----------
async def _maybe_start_engines():
    try:
        from engines import rei_dispo_engine, govcon_subtrap_engine
    except Exception:
        return
    try:
        app.state.t_rei = asyncio.create_task(rei_dispo_engine.loop_rei())
    except Exception as e:
        post_error(f"REI engine failed start: {e}")
    try:
        app.state.t_gov = asyncio.create_task(govcon_subtrap_engine.loop_govcon())
    except Exception as e:
        post_error(f"GOVCON engine failed start: {e}")

@app.on_event("startup")
async def on_start():
    post_ops("KRIZZY OPS: startup")
    app.state.hb = asyncio.create_task(heartbeat())
    app.state.wk = asyncio.create_task(worker_loop())
    app.state.eng = asyncio.create_task(_maybe_start_engines())

@app.on_event("shutdown")
async def on_stop():
    for k in ("hb", "wk", "eng", "t_rei", "t_gov"):
        t = getattr(app.state, k, None)
        if t:
            t.cancel()

