from src.common.discord_notify import notify_error, notify_ops
from src.engines.rei_engine import run_rei_engine
from src.engines.govcon_engine import run_govcon_engine


class CommandBus:
    def __init__(self):
        self.registry = {
            "rei": run_rei_engine,
            "govcon": run_govcon_engine,
        }

    async def dispatch(self, command: str, payload=None):
        try:
            if command not in self.registry:
                raise ValueError(f"Unknown command: {command}")

            handler = self.registry[command]
            result = await handler(payload) if payload else await handler()
            notify_ops(f"Command executed: {command}")
            return result

        except Exception as e:
            notify_error(f"CommandBus Error [{command}]: {e}")
            return {"error": str(e)}

