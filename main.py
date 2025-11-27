"""KRIZZY OPS — Minimal web endpoint for Railway"""
from fastapi import FastAPI
from src.common.airtable_client import AirtableClient

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
    """Health check with Airtable status"""
    try:
        client = AirtableClient()
        airtable_ok = client.ping()
    except Exception as e:
        airtable_ok = False
        print(f"[HEALTH] Airtable check failed: {e}")
    
    return {
        "status": "healthy" if airtable_ok else "degraded",
        "airtable": "connected" if airtable_ok else "disconnected"
    }
