import threading
import time
import requests
from utils.discord_utils import post_error

watchdog_lock = threading.Lock()

def run_watchdog_loop():
    while True:
        try:
            r = requests.get("http://127.0.0.1:8080/health", timeout=4)
            if r.status_code != 200:
                post_error("⚠️ Watchdog: healthcheck failed")
        except:
            post_error("⚠️ Watchdog: server unreachable")
        time.sleep(30)
