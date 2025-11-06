import json, os, urllib.request

OPS_URL = os.getenv("DISCORD_OPS_WEBHOOK_URL", "")
ERR_URL = os.getenv("DISCORD_ERRORS_WEBHOOK_URL", "")

def _mask(s: str) -> str:
    if not s: return s
    for k in ("OPENAI_API_KEY","AIRTABLE_API_KEY"):
        v = os.getenv(k)
        if v: s = s.replace(v, "[REDACTED]")
    return s

def _post(url: str, content: str):
    if not url: return
    body = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=8):
            pass
    except Exception:
        pass

def post_ops(msg: str): _post(OPS_URL, _mask(msg))
def post_error(msg: str): _post(ERR_URL, _mask(f":warning: {msg}"))
