# utils/watchdog.py
import asyncio
import logging
from typing import Callable

logger = logging.getLogger(__name__)

async def watchdog_loop(interval: int, on_ping: Callable):
    """
    Background watchdog that calls on_ping() every interval seconds
    """
    logger.info(f"Watchdog started with {interval}s interval")
    
    while True:
        try:
            await asyncio.sleep(interval)
            on_ping()
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
