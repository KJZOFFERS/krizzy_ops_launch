# src/app.py
# Minimal hardened FastAPI app for KRIZZY OPS

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from typing import Dict, Any


app = FastAPI(
    title="KRIZZY OPS",
    version="1.0.0",
    description="REI Dispo + GovCon Sub-Trap Automation Platform"
)


@app.get("/")
def root() -> Dict[str, Any]:
    return {"krizzy_ops": "online"}


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.get("/health/deep")
async def health_deep() -> Dict[str, Any]:
    """
    Deep health check.
    Never throws – always returns JSON with integration statuses.
    """
    results: Dict[str, Any] = {"status": "ok", "integrations": {}}

    # Airtable
    try:
        from src.common.airtable_client import get_airtable
        at = get_airtable()
        results["integrations"]["airtable"] = (
            "configured" if at is not None else "not_configured"
        )
    except Exception as e:
        results["integrations"]["airtable"] = f"error: {e}"

    # Discord
    try:
        from src.common.discord_notify import get_webhook_status
        results["integrations"]["discord"] = get_webhook_status()
    except Exception as e:
        results["integrations"]["discord"] = f"error: {e}"

    # Twilio
    try:
        from src.common.twilio_client import get_twilio
        tw = get_twilio()
        results["integrations"]["twilio"] = (
            "configured" if tw is not None else "not_configured"
        )
    except Exception as e:
        results["integrations"]["twilio"] = f"error: {e}"

    # GitHub
    try:
        from src.tools.github_client import get_github_client
        gh = get_github_client()
        results["integrations"]["github"] = (
            "configured" if gh is not None else "not_configured"
        )
    except Exception as e:
        results["integrations"]["github"] = f"error: {e}"

    return results


@app.get("/rei")
async def rei() -> Any:
    """
    REI Dispo Engine entrypoint.
    All heavy imports and Airtable calls happen inside the engine.
    """
    from src.engines.rei_engine import run_rei_engine
    result = await run_rei_engine()
    # Ensure consistent JSON response
    if isinstance(result, dict):
        return JSONResponse(result)
    return result


@app.get("/govcon")
async def govcon() -> Any:
    """
    GovCon Sub-Trap Engine entrypoint.
    """
    from src.engines.govcon_engine import run_govcon_engine
    result = await run_govcon_engine()
    if isinstance(result, dict):
        return JSONResponse(result)
    return result
