# FILE: utils/discord_utils.py
from __future__ import annotations
import httpx, os

try:
    from config import CFG
except Exception:
    CFG = None

def _targets(kind: str) -> list[str]:
    if CFG:
        if kind == "ops" and CFG.DISCORD_WEBHOOK_OPS:
            return CFG.DISCORD_WEBHOOK_OPS
        if kind == "errors" and CFG.DISCORD_WEBHOOK_ERRORS:
            return CFG.DISCORD_WEBHOOK_ERRORS
    env = "DISCORD_OPS_WEBHOOK_URL" if kind == "ops" else "DISCORD_ERRORS_WEBHOOK_URL"
    v = os.getenv(env, "")
    return [v] if v else []

def _post(url: str, content: str):
    try:
        with httpx.Client(timeout=10) as c:
            c.post(url, json={"content": content})
    except Exception:
        pass  # never block app on Discord failure

def post_ops(msg: str):
    for u in _targets("ops"):
        _post(u, msg)

def post_error(msg: str):
    for u in _targets("errors"):
        _post(u, f"❗ {msg}")
