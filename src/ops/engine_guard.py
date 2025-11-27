# src/ops/engine_guard.py

import time
import traceback
from functools import wraps
from typing import Dict, Any, Callable
from datetime import datetime

from .ops_notify import send_crack

_ENGINE_STATE: Dict[str, Dict[str, Any]] = {}


def engine_enabled(engine_name: str) -> bool:
    """Check if engine is enabled (not in backoff)"""
    state = _ENGINE_STATE.get(engine_name)
    if not state:
        return True
    if not state.get("disabled"):
        return True
    
    disable_until = state.get("disable_until", 0)
    if time.time() >= disable_until:
        state["disabled"] = False
        state["consecutive_failures"] = 0
        return True
    
    return False


def guard_engine(
    engine_name: str,
    max_consecutive_failures: int = 5,
    disable_seconds: int = 600,
):
    """
    Decorator to guard engine runs with circuit breaker pattern.
    
    - Catches all exceptions
    - Tracks consecutive failures
    - Disables engine for disable_seconds after max_consecutive_failures
    - Reports all cracks to Discord
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if engine_name not in _ENGINE_STATE:
                _ENGINE_STATE[engine_name] = {
                    "consecutive_failures": 0,
                    "disabled": False,
                    "disable_until": 0,
                    "total_runs": 0,
                    "total_failures": 0,
                }
            
            state = _ENGINE_STATE[engine_name]
            
            if not engine_enabled(engine_name):
                remaining = int(state["disable_until"] - time.time())
                print(f"[{engine_name}] Engine disabled, re-enabling in {remaining}s")
                return None
            
            state["total_runs"] += 1
            
            try:
                result = func(*args, **kwargs)
                state["consecutive_failures"] = 0
                return result
            
            except Exception as e:
                state["total_failures"] += 1
                state["consecutive_failures"] += 1
                
                tb = traceback.format_exc()
                error_msg = f"{type(e).__name__}: {str(e)}"
                
                meta = {
                    "consecutive_failures": state["consecutive_failures"],
                    "total_failures": state["total_failures"],
                    "total_runs": state["total_runs"],
                    "traceback": tb[-1000:],
                }
                
                send_crack(engine_name, error_msg, meta)
                print(f"[{engine_name}] ERROR: {error_msg}")
                
                if state["consecutive_failures"] >= max_consecutive_failures:
                    state["disabled"] = True
                    state["disable_until"] = time.time() + disable_seconds
                    send_crack(
                        engine_name,
                        f"DISABLED for {disable_seconds}s after {max_consecutive_failures} consecutive failures",
                        {"re_enable_at": datetime.fromtimestamp(state["disable_until"]).isoformat()}
                    )
                    print(f"[{engine_name}] DISABLED for {disable_seconds}s")
                
                return None
        
        return wrapper
    return decorator
