# utils/heartbeat.py
import os, time
from .discord_utils import post_ops

SERVICE_NAME = os.getenv("SERVICE_NAME", "krizzy_ops_web")

def heartbeat() -> dict:
    ts = int(time.time())
    post_ops(f"{SERVICE_NAME} heartbeat {ts}")
    return {"ok": True, "ts": ts, "service": SERVICE_NAME}
