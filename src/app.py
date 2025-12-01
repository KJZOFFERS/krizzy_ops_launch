from fastapi import FastAPI
from src.tools.repo_write import router as repo_write_router
from src.engines.rei_engine import run_rei_engine

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"krizzy_ops": "online"}

@app.get("/engine/rei")
async def rei():
    return await run_rei_engine()

# mount repo-write routes (safe)
app.include_router(repo_write_router)
