import asyncio
from rei_dispo_engine import run_rei_dispo
from govcon_subtrap_engine import run_govcon_subtrap
from watchdog import watchdog_loop
from healthcheck import start_health_server

async def main():
    await asyncio.gather(
        run_rei_dispo(),
        run_govcon_subtrap(),
        watchdog_loop(),
        start_health_server()
    )

if __name__ == "__main__":
    asyncio.run(main())
