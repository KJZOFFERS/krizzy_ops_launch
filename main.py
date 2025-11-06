import os
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from utils.discord_utils import post_ops, post_error
from utils import list_records, upsert_record
from utils.heartbeat import heartbeat
from utils.router import handle_command

SERVICE_NAME = os.getenv("SERVICE_NAME", "krizzy_ops_web")
AT_TABLE_LEADS = os.getenv("AT_TABLE_LEADS_REI", "Leads_REI")
AT_TABLE_BUYERS = os.getenv("AT_TABLE_BUYERS", "Buyers")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()

app = FastAPI(title="KRIZZY OPS Web")

def _enforce_token(req: Request, token_param: str | None):
    if not ADMIN_TOKEN:
        return
    supplied = req.headers.get("X-Admin-Token") or token_param or ""
    if supplied != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="invalid admin token")

@app.get("/")
def index():
    return {"ok": True, "service": SERVICE_NAME,
            "routes": ["/health", "/command", "/ingest/lead", "/match/buyers/{zip}", "/control"]}

@app.get("/health")
def health():
    return {"status": "healthy", "service": SERVICE_NAME}

@app.on_event("startup")
def on_startup():
    try:
        post_ops(f"{SERVICE_NAME} boot OK")
        heartbeat()
    except Exception as e:
        post_error(f"startup error: {e}")

# Command router (POST/GET; token in header or query)
@app.api_route("/command", methods=["POST", "GET"])
@app.api_route("/command/", methods=["POST", "GET"])
async def command(req: Request, input: str | None = Query(default=None), token: str | None = Query(default=None)):
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

# Lead ingest (token-gated)
@app.post("/ingest/lead")
def ingest_lead(req: Request, payload: dict, token: str | None = Query(default=None)):
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

# Buyer match (token-gated)
@app.get("/match/buyers/{zip_code}")
def match_buyers(req: Request, zip_code: str, ask: float = 0, token: str | None = Query(default=None)):
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

# Minimal web console (paste token each time; no storage)
@app.get("/control", response_class=HTMLResponse)
def control():
    return """
<!doctype html><meta charset="utf-8">
<title>KRIZZY OPS Control</title>
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

