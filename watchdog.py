import time, os
from discord_utils import send_error

def start_watchdog():
    while True:
        try:
            time.sleep(300)
            if not os.environ.get("AIRTABLE_API_KEY"):
                raise Exception("Missing env vars")
        except Exception as e:
            send_error(f"Watchdog failure: {e}")
