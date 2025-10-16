# main.py
import asyncio
import logging
from rei_dispo_engine import run_rei_dispo
from govcon_subtrap_engine import run_govcon_subtrap
from watchdog import watchdog_loop
from healthcheck import start_health_server

async def main():
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s %(message)s')
    # run forever
    await asyncio.gather(
        run_rei_dispo(),          # async loop
        run_govcon_subtrap(),     # async loop
        watchdog_loop(),          # async loop
        start_health_server()     # aiohttp server on :8080/health
    )

if __name__ == "__main__":
    asyncio.run(main())

