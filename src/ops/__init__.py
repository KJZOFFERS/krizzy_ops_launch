# src/ops/__init__.py

from __future__ import annotations

from typing import Any, Dict, Optional

from .ops_notify import (
    send_ops,
    send_error,
    send_trade,
    send_health,
)
from .engine_guard import guard_engine
from .preflight import run_preflight


def send_crack(
    source: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Centralized CRACK notifier.

    All engines call this with:
      - source: short engine/service name ("rei_engine", "govcon_engine", "ops_health", etc.)
      - message: human-readable description of the issue
      - context: optional dict with extra fields (record IDs, phone, status codes, etc.)

    Implementation: wrap underlying error notifier so all cracks
    show up in the same Discord/error channel.
    """
    full_message = f"[CRACK][{source}] {message}"
    if context:
        full_message += f" | ctx={context}"

    # Delegate to the existing error notifier
    send_error(full_message)


__all__ = [
    "send_ops",
    "send_error",
    "send_trade",
    "send_health",
    "send_crack",
    "guard_engine",
    "run_preflight",
]
