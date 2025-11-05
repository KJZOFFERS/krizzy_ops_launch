import os
from .discord_utils import post_ops

SERVICE_NAME = os.getenv("SERVICE_NAME", "krizzy_ops_web")

def heartbeat() -> None:
    try:
        post_ops(f"{SERVICE_NAME} heartbeat")
    except Exception:
        # Avoid crashing app on ops failures.
        pass
