import os, random
from typing import Optional

def get_proxy() -> Optional[str]:
    pool = [p.strip() for p in os.getenv("PROXY_ROTATE_POOL", "").split(",") if p.strip()]
    return random.choice(pool) if pool else None
