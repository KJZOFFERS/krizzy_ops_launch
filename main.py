from fastapi import FastAPI
import threading, time, os
from utils.watchdog import start_watchdog
from utils.kpi import kpi_push
from utils.validate_env import validate_env

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "running", "ts": int(time.time())}

@app.on_event("startup")
async def startup_event():
    # Check environment keys before running anything
    validate_env([
        "AIRTABLE_API_KEY",
        "AIRTABLE_BASE_ID",
        "DISCORD_WEBHOOK_OPS",
        "DISCORD_WEBHOOK_ERRORS",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_MESSAGING_SERVICE_SID"
    ])
    # Start watchdog in background
    threading.Thread(target=start_watchdog, daemon=True).start()
    # Log boot KPI
    kpi_push(event="boot", data={"service": "krizzy_ops"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
