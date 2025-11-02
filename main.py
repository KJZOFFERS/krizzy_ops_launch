from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/healthz")
def healthz():
    return {"status": "healthy", "service": "krizzy_ops_web"}

@app.post("/run/rei")
async def run_rei():
    from worker import rei_cycle
    await rei_cycle()
    return {"rei": "cycle executed"}

@app.post("/run/govcon")
async def run_govcon():
    from worker import govcon_cycle
    await govcon_cycle()
    return {"govcon": "cycle executed"}
