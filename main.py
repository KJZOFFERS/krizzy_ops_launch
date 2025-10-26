from fastapi import FastAPI
import asyncio, os, time

app = FastAPI()

@app.get("/health")
async def health():
    """Simple check so Railway can confirm the container is alive."""
    return {"status": "running", "timestamp": int(time.time())}

async def background_tasks():
    """Simulates the main operational loop."""
    while True:
        # Add your real engines here later
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_tasks())

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
