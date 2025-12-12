import os
import requests

OPS = os.getenv("DISCORD_WEBHOOK_OPS", "")
ERR = os.getenv("DISCORD_WEBHOOK_ERRORS", "")

def post_ops(msg):
    if OPS:
        requests.post(OPS, json={"content": msg})

def post_error(msg):
    if ERR:
        requests.post(ERR, json={"content": msg})
