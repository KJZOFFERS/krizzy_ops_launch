import asyncio, time, os, requests

START = time.time()
LAST = START

async def start_watchdog():
    global LAST
    while True:
        await asyncio.sleep(int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "60")))
        lag_val = round(time.time() - LAST, 2)
        try:
            requests.post(os.getenv("DISCORD_WEBHOOK_OPS"),
                          json={"content": f"Heartbeat ok | lag={lag_val}s"})
        except Exception:
            pass
        LAST = time.time()

def uptime(): return round(time.time() - START, 1)
def lag(): return round(time.time() - LAST, 2)
