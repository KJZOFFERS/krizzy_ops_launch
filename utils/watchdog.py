import time
from utils.discord_utils import post_error

last_watchdog_ping = None

def loop_watchdog():
    global last_watchdog_ping
    last_watchdog_ping = int(time.time())
    # If something is wrong, raise alert:
    # post_error("[WATCHDOG] anomaly detected")
