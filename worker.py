import asyncio, logging
from utils.discord_utils import post_error

def notify(message):
    try:
        logging.info(f"Worker notify: {message}")
    except Exception as e:
        logging.error(f"Notification failed: {e}")

async def worker_loop():
    while True:
        try:
            logging.info("KRIZZY OPS worker running...")
            await asyncio.sleep(60)
        except Exception as e:
            post_error(f"Worker loop error: {e}")

