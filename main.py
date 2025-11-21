"""KRIZZY OPS — Minimal web endpoint for Railway"""
from fastapi import FastAPI

app = FastAPI(title="KRIZZY OPS")

@app.get("/")
def root():
    return {
        "service": "krizzy_ops",
        "status": "online",
        "workers": ["ops_health", "govcon_subtrap", "rei_dispo"]
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
```

### FILE 3: Procfile (UPDATE — add web process)
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
ops_health: python -m src.ops_health_service
govcon: python -m src.govcon_subtrap_engine
rei_dispo: python -m src.rei_dispo_engine
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
ops_health: python -m src.ops_health_service
govcon: python -m src.govcon_subtrap_engine
rei_dispo: python -m src.rei_dispo_engine
