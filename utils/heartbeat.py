import time
from utils.discord_utils import post_ops

def heartbeat():
    msg = f"Heartbeat OK at {time.strftime('%Y-%m-%d %H:%M:%S')}"
    post_ops(msg)
    return {"status": "ok", "timestamp": msg}
