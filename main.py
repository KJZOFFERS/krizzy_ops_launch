from fastapi import FastAPI
import threading, time, os
from engines.rei_dispo_engine import run_rei_dispo
from engines.govcon_subtrap_engine import run_govcon_subtrap
from utils.kpi import kpi_push
from utils.validate_env import validate_env

app = FastAPI()

@app.get("/")
def home():
    return {"status": "online"}

@app.get("/health")
def health():
    return {"status": "running", "ts": int(time.time())}

@app.on_event("startup")
async def startup_event():
    validate_env([
        "AIRTABLE_API_KEY", "AIRTABLE_BASE_ID",
        "DISCORD_WEBHOOK_OPS", "DISCORD_WEBHOOK_ERRORS",
        "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_MESSAGING_SERVICE_SID"
    ])
    kpi_push(event="boot", data={"service": "krizzy_ops"})
    threading.Thread(target=run_rei_dispo, daemon=True).start()
    threading.Thread(target=run_govcon_subtrap, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
