import requests, os

def post_to_discord(channel, message):
    webhook = os.getenv(f"DISCORD_WEBHOOK_{channel.upper()}")
    if not webhook:
        return
    try:
        requests.post(webhook, json={"content": message}, timeout=10)
    except Exception:
        pass
