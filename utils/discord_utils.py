import requests, os

def send_discord_message(content, channel="ops"):
    webhook = {
        "ops": os.getenv("DISCORD_WEBHOOK_OPS"),
        "errors": os.getenv("DISCORD_WEBHOOK_ERRORS"),
        "trades": os.getenv("DISCORD_WEBHOOK_TRADES")
    }.get(channel)
    if webhook:
        requests.post(webhook, json={"content": content})
