import os
import json
import logging
import requests

OPS_HOOK = os.getenv("DISCORD_WEBHOOK_OPS")
ERR_HOOK = os.getenv("DISCORD_WEBHOOK_ERRORS")

TIMEOUT = 10

def _post(webhook: str | None, content: str, embeds=None):
    if not webhook:
        logging.info(f"[DISCORD SKIP] {content}")
        return False
    payload = {"content": content}
    if embeds:
        payload["embeds"] = embeds
    resp = requests.post(webhook, json=payload, timeout=TIMEOUT)
    if resp.status_code >= 400:
        logging.error(f"Discord post failed {resp.status_code}: {resp.text}")
        return False
    return True

def post_ops(msg: str, extra: dict | None = None):
    embeds = None
    if extra:
        embeds = [{"description": "```json\n" + json.dumps(extra, indent=2) + "\n```"}]
    return _post(OPS_HOOK, msg, embeds)

def post_error(msg: str, extra: dict | None = None):
    embeds = None
    if extra:
        embeds = [{"description": "```json\n" + json.dumps(extra, indent=2) + "\n```"}]
    return _post(ERR_HOOK, f"**ERROR:** {msg}", embeds)
