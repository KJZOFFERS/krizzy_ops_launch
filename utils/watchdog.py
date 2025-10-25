import time, threading, requests, os
from utils.discord_utils import send_discord_message

def health_ping():
    while True:
        try:
            r = requests.get(f"{os.getenv('RAILWAY_URL')}/health", timeout=10)
            if r.status_code != 200:
                send_discord_message("⚠️ Healthcheck failed", "errors")
        except Exception as e:
            send_discord_message(f"Watchdog error: {e}", "errors")
        time.sleep(300)

def start_watchdog():
    threading.Thread(target=health_ping, daemon=True).start()
