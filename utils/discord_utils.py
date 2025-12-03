import os
import requests

OPS = os.environ["DISCORD_WEBHOOK_OPS"]
ERR = os.environ["DISCORD_WEBHOOK_ERRORS"]

def post_ops(msg):
    requests.post(OPS, json={"content": msg})

def post_error(msg):
    requests.post(ERR, json={"content": msg})
