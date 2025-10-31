import time
from utils.discord_utils import post_ops

last_rei_run = None

def loop_rei():
    global last_rei_run

    # --- YOUR REI PROCESSING LOGIC LIVES HERE ---
    # Do not delete. Replace with your actual REI workflow when ready.

    last_rei_run = int(time.time())
    post_ops(f"[REI] cycle complete at {last_rei_run}")
