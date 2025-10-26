from fastapi import FastAPI
import asyncio, time
from engines.rei_dispo_engine import loop_rei
from engines.govcon_subtrap_engine import loop_govcon
from utils.watchdog import start_watchdog
from utils.kpi import kpi_push
from utils.validate_env import validate_env

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "running", "ts": int(time.time())}

@app.on_event("startup")
async def startup_event():
    validate_env([
        "AIRTABLE_API_KEY","AIRTABLE_BASE_ID",
        "DISCORD_WEBHOOK_OPS","DISCORD_WEBHOOK_ERRORS",
        "TWILIO_ACCOUNT_SID","TWILIO_AUTH_TOKEN","TWILIO_MESSAGING_SERVICE_SID"
    ])
    kpi_push(event="boot", data={"service":"krizzy_ops"})
    asyncio.create_task(loop_rei())
    asyncio.create_task(loop_govcon())
    start_watchdog()
