# src/ops/__init__.py

import json
import os
import urllib.request
import urllib.error


WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS")
WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS")
WEBHOOK_TRADES = os.getenv("DISCORD_WEBHOOK_TRADES")


def _post_webhook(url: str | None, payload: dict) -> None:
    if not url:
        # Fail silently if no webhook configured
        return

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        # Never let ops logging crash the engine
        pass


def send_ops(message: str, level: str = "INFO", extra: dict | None = None) -> None:
    """
    Main ops logger used across the stack.
    Keeps signature: send_ops(message, level="INFO", extra=None)
    """
    content = f"[{level}] {message}"
    payload: dict = {"content": content}

    if extra:
        # Put structured context into an embed
        payload["embeds"] = [
            {
                "description": json.dumps(extra, ensure_ascii=False, indent=2),
            }
        ]

    _post_webhook(WEBHOOK_OPS, payload)


def send_error(message: str, extra: dict | None = None) -> None:
    """
    Error-level logger. Falls back to OPS webhook if ERRORS is not set.
    """
    content = f"[ERROR] {message}"
    payload: dict = {"content": content}

    if extra:
        payload["embeds"] = [
            {
                "description": json.dumps(extra, ensure_ascii=False, indent=2),
            }
        ]

    _post_webhook(WEBHOOK_ERRORS or WEBHOOK_OPS, payload)


def send_trade(message: str, extra: dict | None = None) -> None:
    """
    Optional trade/event logger for #trades channel.
    Safe no-op if DISCORD_WEBHOOK_TRADES is not set.
    """
    content = f"[TRADE] {message}"
    payload: dict = {"content": content}

    if extra:
        payload["embeds"] = [
            {
                "description": json.dumps(extra, ensure_ascii=False, indent=2),
            }
        ]

    _post_webhook(WEBHOOK_TRADES or WEBHOOK_OPS, payload)
