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
