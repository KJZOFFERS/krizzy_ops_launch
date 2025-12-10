from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import logging

from app_v2.llm_control import normalizers, scorers, outbound_writer, dev_agent

logger = logging.getLogger(__name__)

router = APIRouter()


class Command(BaseModel):
    """
    LLM Command structure for V2 engine control.

    engine: Target engine ("rei" | "govcon" | "buyers" | "outbound" | "dev")
    action: Action to perform ("run" | "normalize" | "score" | "write" | "fix" | "health")
    payload: Engine-specific parameters
    """
    engine: str
    action: str
    payload: Dict[str, Any] = {}


@router.post("/command")
async def llm_command(cmd: Command) -> Dict[str, Any]:
    """
    Central LLM command bus for V2.

    This is the ONLY endpoint LLM needs to call to control all V2 engines.

    Examples:
      - Run REI engine: {"engine": "rei", "action": "run", "payload": {"batch": 200}}
      - Normalize text: {"engine": "rei", "action": "normalize", "payload": {"text": "..."}}
      - Score deal: {"engine": "rei", "action": "score", "payload": {"arv": 300000, ...}}
      - Generate copy: {"engine": "outbound", "action": "write", "payload": {"role": "rei", ...}}
      - Diagnose error: {"engine": "dev", "action": "fix", "payload": {"error": "422 ..."}}
    """
    try:
        logger.info(f"LLM Command: engine={cmd.engine}, action={cmd.action}")

        if cmd.engine == "rei":
            return await _handle_rei(cmd.action, cmd.payload)
        elif cmd.engine == "govcon":
            return await _handle_govcon(cmd.action, cmd.payload)
        elif cmd.engine == "buyers":
            return await _handle_buyers(cmd.action, cmd.payload)
        elif cmd.engine == "outbound":
            return await _handle_outbound(cmd.action, cmd.payload)
        elif cmd.engine == "dev":
            return await _handle_dev(cmd.action, cmd.payload)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown engine '{cmd.engine}'. Valid: rei, govcon, buyers, outbound, dev"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("LLM command error")
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_rei(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle REI engine commands"""

    if action == "run":
        # Trigger input + underwriting cycle
        from app_v2.engines.input_engine import InputEngine
        from app_v2.engines.underwriting_engine import run_underwriting_cycle

        batch_size = int(payload.get("batch", 100))

        # Run input cycle
        input_engine = InputEngine()
        input_result = input_engine.run_input_cycle()

        # Run underwriting cycle
        underwriting_result = run_underwriting_cycle()

        return {
            "status": "ok",
            "engine": "rei",
            "action": "run",
            "input": input_result,
            "underwriting": underwriting_result,
        }

    elif action == "normalize":
        normalized = normalizers.normalize_rei(payload)
        return {
            "status": "ok",
            "engine": "rei",
            "action": "normalize",
            "normalized": normalized,
        }

    elif action == "score":
        score = scorers.score_rei(payload)
        return {
            "status": "ok",
            "engine": "rei",
            "action": "score",
            "score": score,
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown REI action '{action}'. Valid: run, normalize, score"
        )


async def _handle_govcon(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle GovCon engine commands"""

    if action == "run":
        # TODO: Trigger govcon_engine when implemented
        return {
            "status": "not_implemented",
            "engine": "govcon",
            "action": "run",
            "message": "govcon_engine.py not yet implemented",
        }

    elif action == "normalize":
        normalized = normalizers.normalize_govcon(payload)
        return {
            "status": "ok",
            "engine": "govcon",
            "action": "normalize",
            "normalized": normalized,
        }

    elif action == "score":
        score = scorers.score_govcon(payload)
        return {
            "status": "ok",
            "engine": "govcon",
            "action": "score",
            "score": score,
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown GovCon action '{action}'. Valid: run, normalize, score"
        )


async def _handle_buyers(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Buyers engine commands"""

    if action == "run":
        # TODO: Trigger buyer_engine when implemented
        return {
            "status": "not_implemented",
            "engine": "buyers",
            "action": "run",
            "message": "buyer_engine.py not yet implemented",
        }

    elif action == "normalize":
        normalized = normalizers.normalize_buyer(payload)
        return {
            "status": "ok",
            "engine": "buyers",
            "action": "normalize",
            "normalized": normalized,
        }

    elif action == "score":
        score = scorers.score_buyer(payload)
        return {
            "status": "ok",
            "engine": "buyers",
            "action": "score",
            "score": score,
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown Buyers action '{action}'. Valid: run, normalize, score"
        )


async def _handle_outbound(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Outbound engine commands"""

    if action == "write":
        copy = outbound_writer.generate_copy(payload)
        return {
            "status": "ok",
            "engine": "outbound",
            "action": "write",
            "copy": copy,
        }

    elif action == "run":
        # TODO: Trigger outbound_control_engine when implemented
        return {
            "status": "not_implemented",
            "engine": "outbound",
            "action": "run",
            "message": "outbound_control_engine.py not yet implemented",
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown Outbound action '{action}'. Valid: write, run"
        )


async def _handle_dev(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Dev agent commands"""

    if action == "fix":
        fix_suggestion = dev_agent.repair_code(payload)
        return {
            "status": "ok",
            "engine": "dev",
            "action": "fix",
            "diagnosis": fix_suggestion,
        }

    elif action == "schema_fix":
        table = payload.get("table")
        failed_fields = payload.get("failed_fields", [])
        suggestions = dev_agent.suggest_schema_fix(table, failed_fields)
        return {
            "status": "ok",
            "engine": "dev",
            "action": "schema_fix",
            "suggestions": suggestions,
        }

    elif action == "health":
        from app_v2.models.system_state import system_state
        return {
            "status": "ok",
            "engine": "dev",
            "action": "health",
            "system_state": system_state.get_status(),
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown Dev action '{action}'. Valid: fix, schema_fix, health"
        )
