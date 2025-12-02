import os
from typing import Dict, Any

from fastapi import FastAPI

app = FastAPI(title="KRIZZY OPS Core Service")


def check_airtable_ready() -> bool:
    """True if Airtable creds are present."""
    base_id = os.getenv("AIRTABLE_BASE_ID")
    api_key = os.getenv("AIRTABLE_API_KEY")
    return bool(base_id and api_key)


def check_twilio_ready() -> bool:
    """True if Twilio creds are present (but does NOT require Twilio to be used)."""
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    messaging_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
    return bool(sid and token and messaging_sid)


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "status": "ok",
        "engine": "KRIZZY_OPS",
        "services": {
            "rei_dispo": True,
            "govcon_subtrap": True,
            "watchdog": True,
        },
        "integrations": {
            "airtable_ready": check_airtable_ready(),
            "twilio_ready": check_twilio_ready(),
        },
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}
