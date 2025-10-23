import requests, os

def send_ops(msg):
    requests.post(os.environ["DISCORD_WEBHOOK_OPS"], json={"content": msg})

def send_error(msg):
    requests.post(os.environ["DISCORD_WEBHOOK_ERRORS"], json={"content": f"⚠️ {msg}"})
