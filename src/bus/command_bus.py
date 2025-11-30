import time
import traceback
from typing import Dict, Any

from src.engines.rei_engine import run_rei_engine
from src.engines.govcon_engine import run_govcon_engine
from src.tools.discord_notify import notify_ops, notify_error


class CommandBus:
    """
    Central execution router for KRIZZY OPS.
    All engines, loops, cron jobs, and AI actions flow through here.
    """

    def __init__(self):
        self.registry = {
            "REI": run_rei_engine,
            "GOVCON": run_govcon_engine,
        }

    def run(self, command: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        if payload is None:
            payload = {}

        start = time.time()

        if command not in self.registry:
            notify_error(f"[BUS] Unknown command: {command}")
            return {
                "status": "error",
                "error": "UNKNOWN_COMMAND",
                "command": command,
            }

        try:
            notify_ops(f"[BUS] Executing: {command}")
            result = self.registry[command](payload)

            duration = round(time.time() - start, 3)

            notify_ops(f"[BUS] {command} completed in {duration}s")

            return {
                "status": "ok",
                "command": command,
                "duration": duration,
                "result": result,
            }

        except Exception as e:
            tb = traceback.format_exc()
            notify_error(f"[BUS] FAILURE in {command}: {e}\n{tb}")

            return {
                "status": "error",
                "command": command,
                "error": str(e),
                "trace": tb,
            }


# Singleton bus instance
bus = CommandBus()
