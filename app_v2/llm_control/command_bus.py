import logging
from typing import Any, Callable, Dict, Tuple

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

logger = logging.getLogger("krizzy_ops_launch.command_bus")


class Command(BaseModel):
    engine: str
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)


def _rei_run_handler(payload: Dict[str, Any]):
    logger.info("handler started: engine=rei action=run")
    try:
        from engines.rei_engine import run_rei_engine

        run_rei_engine(payload=payload)
        logger.info("handler finished: engine=rei action=run")
        return {
            "status": "dispatched",
            "engine": "rei",
            "action": "run",
        }
    except Exception as exc:
        logger.exception("handler error: engine=rei action=run")
        return {
            "status": "error",
            "engine": "rei",
            "action": "run",
            "error": "handler_exception",
            "detail": str(exc),
        }


HANDLERS: Dict[Tuple[str, str], Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    ("rei", "run"): _rei_run_handler,
}


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

    handler = HANDLERS.get((cmd.engine, cmd.action))

    if not handler:
        logger.warning(
            "handler not found: engine=%s action=%s", cmd.engine, cmd.action
        )
        return {
            "status": "error",
            "error": "handler_not_found",
            "engine": cmd.engine,
            "action": cmd.action,
        }

    logger.info("handler resolved: engine=%s action=%s", cmd.engine, cmd.action)
    return handler(cmd.payload)
