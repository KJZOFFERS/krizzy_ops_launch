import os, requests, json
from dotenv import load_dotenv
load_dotenv()

OPS = os.getenv("DISCORD_WEBHOOK_OPS")
ERR = os.getenv("DISCORD_WEBHOOK_ERRORS")

def post_ops(msg):
    if OPS:
        requests.post(OPS, json={"content": f"✅ {msg}"})

def post_error(msg):
    if ERR:
        requests.post(ERR, json={"content": f"❌ {msg}"})
