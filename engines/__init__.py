# FILE: engines/__init__.py
# Map *_updated.py files to the expected module names used by imports.
try:
    from . import rei_dispo_engine_updated as rei_dispo_engine  # exposes loop_rei()
except Exception:
    class _ReiStub:
        async def loop_rei(self):  # safe no-op
            return None
    rei_dispo_engine = _ReiStub()

try:
    from . import govcon_subtrap_engine_updated as govcon_subtrap_engine  # exposes loop_govcon()
except Exception:
    class _GovStub:
        async def loop_govcon(self):  # safe no-op
            return None
    govcon_subtrap_engine = _GovStub()

__all__ = ["rei_dispo_engine", "govcon_subtrap_engine"]
