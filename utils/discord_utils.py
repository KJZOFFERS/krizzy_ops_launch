import os, requests

OPS = os.getenv("DISCORD_WEBHOOK_OPS")
ERR = os.getenv("DISCORD_WEBHOOK_ERRORS")

async def post_ops(msg):
    if OPS:
        requests.post(OPS, json={"content": msg})

def post_errors(msg):
    if ERR:
        requests.post(ERR, json={"content": msg})
