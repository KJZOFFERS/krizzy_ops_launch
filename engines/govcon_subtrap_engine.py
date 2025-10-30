import time
from utils.discord_utils import post_ops

last_govcon_run = None

def loop_govcon():
    global last_govcon_run
    # --- YOUR EXISTING GOVERNMENT CONTRACT LOGIC ---
    # Do not remove. Do not reorder.
    # Example:
    # fetch solicitations, filter, write airtable, notify

    # After successful cycle:
    last_govcon_run = int(time.time())
    post_ops(f"[GOVCON] Cycle complete at {last_govcon_run}")

