import os, random

def get_proxy():
    pool=[p.strip() for p in os.getenv("PROXY_ROTATE_POOL","").split(",") if p.strip()]
    return random.choice(pool) if pool else None
