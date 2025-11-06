import os
import time
from .discord_utils import post_ops

SERVICE_NAME = os.getenv("SERVICE_NAME", "krizzy_ops_web")

def heartbeat() -> dict:
    ts = int(time.time())
    msg = f"{SERVICE_NAME} heartbeat {ts}"
    try:
        post_ops(msg)
    except Exception:
        # keep startup non-fatal if webhook is absent
        pass
    return {"ok": True, "ts": ts, "service": SERVICE_NAME}
