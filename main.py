import os
from fastapi import FastAPI, HTTPException, Request, Query
from utils.discord_utils import post_ops, post_error
from utils import list_records, upsert_record
from utils.heartbeat import heartbeat
from utils.router import handle_command

SERVICE_NAME = os.getenv("SERVICE_NAME", "krizzy_ops_web")
AT_TABLE_LEADS = os.getenv("AT_TABLE_LEADS_REI", "Leads_REI")
AT_TABLE_BUYERS = os.getenv("AT_TABLE_BUYERS", "Buyers")

app = FastAPI(title="KRIZZY OPS Web")

# Root
@app.get("/")
def index():
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "routes": ["/health", "/command", "/ingest/lead", "/match/buyers/{zip}"],
    }

# Health
@app.get("/health")
def health():
    return {"status": "healthy", "service": SERVICE_NAME}

# Startup
@app.on_event("startup")
def on_startup():
    try:
        post_ops(f"{SERVICE_NAME} boot OK")
        heartbeat()
    except Exception as e:
        post_error(f"startup error: {e}")

# Command router (POST and GET, with and without trailing slash)
@app.api_route("/command", methods=["POST", "GET"])
@app.api_route("/command/", methods=["POST", "GET"])
async def command(req: Request | None = None, input: str | None = Query(default=None)):
    # Prefer POST body; fall back to GET ?input=
    text = None
    if req and req.method == "POST":
        try:
            data = await req.json()
            text = data.get("input")
        except Exception:
            text = None
    if text is None:
        text = input

    if not text:
        raise HTTPException(status_code=400, detail="Missing input")

    try:
        result = handle_command(text)
        return {"ok": True, "input": text, "result": result}
    except Exception as e:
        post_error(f"/command failed: {e}")
        raise HTTPException(status_code=500, detail="command failed")

# Lead ingest
@app.post("/ingest/lead")
def ingest_lead(payload: dict):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body required")
    key = payload.get("key") or payload.get("address") or "MISSING:key"
    payload["key"] = key
    try:
        upsert_record(AT_TABLE_LEADS, "key", str(key), payload)
        return {"ok": True, "key": key}
    except Exception as e:
        post_error(f"/ingest/lead failed: {e}")
        raise HTTPException(status_code=500, detail="ingest failed")

# Buyer match
@app.get("/match/buyers/{zip_code}")
def match_buyers(zip_code: str, ask: float = 0):
    formula = (
        f"AND({{opted_out}} != 1, "
        f"{{zip}} = '{zip_code}', "
        f"OR(NOT({{budget_max}} = ''), {{budget_max}} >= {ask}))"
    )
    try:
        recs = list_records(AT_TABLE_BUYERS, formula=formula, max_records=10)
        phones = [
            r.get("fields", {}).get("phone")
            for r in recs
            if r.get("fields", {}).get("phone")
        ]
        return {"buyers": phones[:10]}
    except Exception as e:
        post_error(f"/match/buyers failed: {e}")
        raise HTTPException(status_code=500, detail="match failed")
