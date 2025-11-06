import os, time
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from utils.discord_utils import post_ops, post_error
from utils import list_records, upsert_record
from utils.heartbeat import heartbeat
from utils.router import handle_command
from utils.airtable_utils import ping as airtable_ping
from utils.metrics import track
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

SERVICE_NAME   = os.getenv("SERVICE_NAME", "krizzy_ops_web")
AT_TABLE_LEADS = os.getenv("AT_TABLE_LEADS_REI", "Leads_REI")
AT_TABLE_BUYERS= os.getenv("AT_TABLE_BUYERS", "Buyers")
ADMIN_TOKEN    = os.getenv("ADMIN_TOKEN", "").strip()
GIT_SHA        = os.getenv("GIT_SHA", "unknown")
DEPLOYED_AT    = os.getenv("DEPLOYED_AT", "")

app = FastAPI(title="KRIZZY OPS Web")

# --- Security + logging headers
@app.middleware("http")
async def harden(request: Request, call_next):
    start = time.time()
    rid = request.headers.get("X-Request-Id", f"req-{int(start*1000)}")
    try:
        response: Response = await call_next(request)
        code = response.status_code
    except Exception as e:
        post_error(f"unhandled: {e}")
        raise
    # headers
    response.headers["X-Request-Id"] = rid
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    # metrics
    finalize = track(request.url.path, request.method)
    finalize(code)
    return response

# --- Simple in-memory rate limit (per IP, burst 20, refill ~1/sec)
_BUCKETS: Dict[str, Dict[str, float]] = {}
def _rate_limit(key: str, cost: float = 1.0):
    now = time.time()
    b = _BUCKETS.get(key, {"tokens": 20.0, "ts": now})
    # refill
    b["tokens"] = min(20.0, b["tokens"] + (now - b["ts"]) * 1.0)
    b["ts"] = now
    if b["tokens"] < cost:
        raise HTTPException(status_code=429, detail="rate limit")
    b["tokens"] -= cost
    _BUCKETS[key] = b

def _enforce_token(req: Request, token_param: Optional[str]):
    if not ADMIN_TOKEN:
        return
    supplied = req.headers.get("X-Admin-Token") or token_param or ""
    if supplied != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="invalid admin token")

@app.get("/")
def index():
    return {"ok": True, "service": SERVICE_NAME, "version": GIT_SHA, "deployed_at": DEPLOYED_AT,
            "routes": ["/health","/ready","/metrics","/command","/ingest/lead","/match/buyers/{zip}","/control"]}

@app.get("/health")
def health():
    return {"status":"healthy","service":SERVICE_NAME}

@app.get("/ready")
def ready():
    ok = airtable_ping(AT_TABLE_LEADS)
    return {"ready": ok, "service": SERVICE_NAME}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.on_event("startup")
def on_startup():
    try:
        post_ops(f"{SERVICE_NAME} boot OK @ {GIT_SHA or 'dev'}")
        heartbeat()
    except Exception as e:
        post_error(f"startup error: {e}")

@app.api_route("/command", methods=["POST","GET"])
@app.api_route("/command/", methods=["POST","GET"])
async def command(req: Request, input: Optional[str] = Query(default=None), token: Optional[str] = Query(default=None)):
    _rate_limit(req.client.host + ":cmd")
    _enforce_token(req, token)
    text = None
    if req.method == "POST":
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

@app.post("/ingest/lead")
def ingest_lead(req: Request, payload: dict, token: Optional[str] = Query(default=None)):
    _rate_limit(req.client.host + ":ingest")
    _enforce_token(req, token)
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

@app.get("/match/buyers/{zip_code}")
def match_buyers(req: Request, zip_code: str, ask: float = 0, token: Optional[str] = Query(default=None)):
    _rate_limit(req.client.host + ":match")
    _enforce_token(req, token)
    formula = (
        f"AND({{opted_out}} != 1, "
        f"{{zip}} = '{zip_code}', "
        f"OR(NOT({{budget_max}} = ''), {{budget_max}} >= {ask}))"
    )
    try:
        recs = list_records(AT_TABLE_BUYERS, formula=formula, max_records=10)
        phones = [r.get("fields", {}).get("phone") for r in recs if r.get("fields", {}).get("phone")]
        return {"buyers": phones[:10]}
    except Exception as e:
        post_error(f"/match/buyers failed: {e}")
        raise HTTPException(status_code=500, detail="match failed")

@app.get("/control", response_class=HTMLResponse)
def control():
    return """
<!doctype html><meta charset="utf-8"><title>KRIZZY OPS Control</title>
<style>body{font-family:ui-sans-serif,system-ui;margin:40px;max-width:720px}
input,textarea,button{font:inherit;padding:8px;margin:6px 0;width:100%}pre{white-space:pre-wrap;border:1px solid #ddd;padding:12px}</style>
<h2>KRIZZY OPS Control</h2>
<label>Admin Token</label><input id="tok" type="password" placeholder="X-Admin-Token">
<label>Command</label><textarea id="cmd" rows="3" placeholder='e.g. STRAT: test all engines'></textarea>
<button onclick="send()">Send</button>
<pre id="out"></pre>
<script>
async function send(){
  const tok=document.getElementById('tok').value;
  const cmd=document.getElementById('cmd').value;
  const res=await fetch('/command',{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Token':tok},body:JSON.stringify({input:cmd})});
  const txt=await res.text(); document.getElementById('out').textContent=txt;
}
</script>
"""

