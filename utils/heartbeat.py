import os, time
from .discord_utils import post_ops

SERVICE_NAME = os.getenv("SERVICE_NAME", "krizzy_ops_web")

def heartbeat() -> dict:
    ts = int(time.time())
    try:
        post_ops(f"{SERVICE_NAME} heartbeat {ts}")
    except Exception:
        pass
    return {"ok": True, "ts": ts, "service": SERVICE_NAME}
