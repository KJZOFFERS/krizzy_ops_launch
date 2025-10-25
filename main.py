from fastapi import FastAPI
import asyncio, threading
from utils.watchdog import start_watchdog
from utils.kpi import log_kpi
from engines.rei_dispo_engine import run_rei_dispo
from engines.govcon_subtrap_engine import run_govcon

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

async def main_loop():
    while True:
        await asyncio.gather(
            run_rei_dispo(),
            run_govcon(),
        )
        await asyncio.sleep(300)

def on_startup():
    threading.Thread(target=start_watchdog, daemon=True).start()
    log_kpi("system_boot", {"status": "live"})
    asyncio.run(main_loop())

if __name__ == "__main__":
    on_startup()
