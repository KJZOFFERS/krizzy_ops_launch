import time
from utils.discord_utils import post_ops

last_rei_run = None

def loop_rei():
    global last_rei_run
    # --- YOUR EXISTING REI LOGIC GOES HERE ---
    # Do not remove. Do not reorder.
    # Example:
    # process leads, update airtable, send blasts, etc.

    # After successful cycle:
    last_rei_run = int(time.time())
    post_ops(f"[REI] Cycle complete at {last_rei_run}")
