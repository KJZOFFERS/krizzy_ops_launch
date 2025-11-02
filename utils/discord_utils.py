import os
import requests

WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS")
WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS")

def post_ops(msg: str):
    if WEBHOOK_OPS:
        requests.post(WEBHOOK_OPS, json={"content": msg})

def post_error(msg: str):
    if WEBHOOK_ERRORS:
        requests.post(WEBHOOK_ERRORS, json={"content": msg})


def send_message(text: str, channel: str = "ops"):
    """Compatibility shim used by data_extraction.py."""
    if channel == "error":
        return post_error(text)
    return post_ops(text)
