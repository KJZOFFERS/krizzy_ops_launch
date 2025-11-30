# src/app.py
import uvicorn
from fastapi import FastAPI, HTTPException
from src.common.airtable_client import AirtableClient
from src.common.discord import DiscordOps
from src.common.twilio_client import TwilioClient
from src.common.kpi_logger import KPILogger
from src.common.cracks_tracker import CracksTracker
from src.engines.rei_engine import REIEngine
from src.engines.govcon_engine import GovConEngine

# Tools Layer Routers
from src.tools.repo_write import router as write_router
from src.tools.repo_diff import router as diff_router
from src.tools.schema_sync import router as schema_router
from src.tools.deploy import router as deploy_router
from src.tools.fix_crack import router as crack_router


app = FastAPI(title="KRIZZY OPS")


# ---------------------------------------------------------
# INIT CORE CLIENTS
# ---------------------------------------------------------

airtable = AirtableClient()
discord = DiscordOps()
twilio = TwilioClient()
kpi = KPILogger(airtable)
cracks = CracksTracker(airtable, discord)

rei_engine = REIEngine(airtable, discord, twilio, kpi)
gov_engine = GovConEngine(airtable, discord, kpi)


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/")
async def root():
    return {"status": "ok", "service": "KRIZZY OPS"}


# ---------------------------------------------------------
# ENGINE EXECUTION ENDPOINTS
# ---------------------------------------------------------

@app.post("/run_engine")
async def run_engine(engine: str):
    try:
        if engine.lower() == "rei":
            return await rei_engine.run()
        if engine.lower() == "govcon":
            return await gov_engine.run()
        raise HTTPException(400, f"Unknown engine: {engine}")
    except Exception as e:
        await cracks.log("Engine Failure", str(e))
        raise


# ---------------------------------------------------------
# INCLUDE TOOLS LAYER ROUTES
# ---------------------------------------------------------

app.include_router(write_router)
app.include_router(diff_router)
app.include_router(schema_router)
app.include_router(deploy_router)
app.include_router(crack_router)
