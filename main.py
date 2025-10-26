from fastapi import FastAPI
import time

app = FastAPI()

@app.get("/")
async def home():
    return {"status": "online"}

@app.get("/health")
async def health():
    return {"status": "running", "timestamp": int(time.time())}
