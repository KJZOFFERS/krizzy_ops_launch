"""Minimal web endpoint for Railway health checks"""
from fastapi import FastAPI

app = FastAPI(title="KRIZZY OPS Health")

@app.get("/")
def root():
    return {"status": "online", "services": ["ops_health", "govcon", "rei_dispo"]}

@app.get("/health")
def health():
    return {"ok": True}
```

=== requirements.txt (add these lines) ===
```
pyairtable==2.3.3
requests==2.32.3
python-dateutil==2.9.0.post0
feedparser==6.0.11
twilio==9.3.4
fastapi==0.115.5
uvicorn[standard]==0.30.6
```

=== Procfile (UPDATE - add web process) ===
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
ops_health: python -m src.ops_health_service
govcon: python -m src.govcon_subtrap_engine
rei_dispo: python -m src.rei_dispo_engine
