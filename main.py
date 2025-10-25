from fastapi import FastAPI
from utils.watchdog import start_watchdog
from utils.kpi import kpi_push
from utils.validate_env import validate_env
import threading, time, os

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "running", "ts": int(time.time())}

@app.on_event("startup")
async def startup_event():
    validate_env(["AIRTABLE_API_KEY","AIRTABLE_BASE_ID",
                  "DISCORD_WEBHOOK_OPS","DISCORD_WEBHOOK_ERRORS"])
    threading.Thread(target=start_watchdog, daemon=True).start()
    kpi_push(event="boot", data={"service":"krizzy_ops"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
