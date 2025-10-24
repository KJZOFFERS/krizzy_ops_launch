import requests, os

def send_message(channel_env, message):
    url = os.getenv(channel_env)
    if not url:
        return
    try:
        requests.post(url, json={"content": message})
    except Exception:
        pass
