# src/__init__.py

"""
KRIZZY OPS package initializer.

Do NOT import submodules directly here that don't exist at the top level
(e.g. 'src.ops_notify'). All ops-related symbols are exposed via src.ops.
"""

from __future__ import annotations

from .ops import (  # type: ignore[attr-defined]
    send_ops,
    send_error,
    send_trade,
    send_crack,
    send_health,
    guard_engine,
    run_preflight,
)

__all__ = [
    "send_ops",
    "send_error",
    "send_trade",
    "send_crack",
    "send_health",
    "guard_engine",
    "run_preflight",
]
