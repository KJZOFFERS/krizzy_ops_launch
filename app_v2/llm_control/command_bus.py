print("COMMAND_BUS_LOADED_WITH_REI_RUN_HANDLER")

from typing import Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Command(BaseModel):
    engine: str
    action: str
    payload: Dict[str, Any] = {}


@router.post("/command")
async def llm_command(cmd: Command):
    """
    Minimal, safe V2 LLM command bus.

    - No external imports (Airtable, Twilio, normalizers, scorers, etc.).
    - Guarantees a clean JSON response for dev/health.
    - Other commands return a structured "unsupported_command" error for now.
    """

    # Health check for V2 control layer
    if cmd.engine == "dev" and cmd.action == "health":
        return {
            "status": "ok",
            "engine": cmd.engine,
            "action": cmd.action,
            "message": "V2 LLM command bus is reachable",
        }

    # REI engine dispatch
    if cmd.engine == "rei" and cmd.action == "run":
        print("REI RUN COMMAND HANDLER HIT")
        from app_v2.engines.rei.run import run_rei_engine
        run_rei_engine(payload=cmd.payload)
        return {
            "status": "dispatched",
            "engine": "rei",
            "action": "run",
        }

    # Stub for everything else (you can expand this later)
    return {
        "status": "error",
        "error": "unsupported_command",
        "engine": cmd.engine,
        "action": cmd.action,
    }
