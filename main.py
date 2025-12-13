import threading
from fastapi import FastAPI, HTTPException
from database import engine, SessionLocal, Base
from scheduler import scheduler_loop
from worker import worker_loop

app = FastAPI()

DAEMONS_STARTED = False

def start_daemons():
    global DAEMONS_STARTED

    try:
        scheduler_thread = threading.Thread(
            target=scheduler_loop,
            args=(SessionLocal,),
            daemon=True
        )
        worker_thread = threading.Thread(
            target=worker_loop,
            args=(SessionLocal,),
            daemon=True
        )

        scheduler_thread.start()
        worker_thread.start()

        DAEMONS_STARTED = True

    except Exception as e:
        DAEMONS_STARTED = False
        raise RuntimeError(f"Failed to start daemons: {e}")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    start_daemons()

@app.get("/health")
def health():
    if not DAEMONS_STARTED:
        raise HTTPException(
            status_code=500,
            detail="Execution kernel not running"
        )
    return {
        "status": "ok",
        "daemons_started": True
    }
