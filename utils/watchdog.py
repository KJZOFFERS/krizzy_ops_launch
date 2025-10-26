import threading, time
from utils.discord_utils import post_errors

def start_watchdog():
    def loop():
        while True:
            time.sleep(1800)
            post_errors("🟢 Watchdog check: system stable")
    threading.Thread(target=loop, daemon=True).start()
