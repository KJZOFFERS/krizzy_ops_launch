"""Discord webhook utilities for ops and error notifications."""

import os
import time
import random
from typing import Optional
import requests
from requests.exceptions import HTTPError


DISCORD_WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS")
DISCORD_WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS")


def _exponential_backoff_with_jitter(
    attempt: int, base_delay: float = 1.0, max_delay: float = 16.0
) -> float:
    """Calculate exponential backoff with jitter."""
    delay = min(base_delay * (2**attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter


def _send_webhook(url: Optional[str], message: str, max_retries: int = 3) -> bool:
    """Send message to Discord webhook with retry logic."""
    if not url:
        return False

    for attempt in range(max_retries):
        try:
            response = requests.post(
                url, json={"content": message}, timeout=10
            )
            response.raise_for_status()
            return True
        except HTTPError as e:
            if e.response and e.response.status_code == 429:
                retry_after = float(e.response.headers.get("Retry-After", 1))
                time.sleep(retry_after)
                continue
            elif attempt < max_retries - 1:
                delay = _exponential_backoff_with_jitter(attempt)
                time.sleep(delay)
                continue
            return False
        except Exception:
            if attempt < max_retries - 1:
                delay = _exponential_backoff_with_jitter(attempt)
                time.sleep(delay)
                continue
            return False

    return False


def post_ops(message: str) -> bool:
    """
    Post operational message to Discord ops channel.

    Args:
        message: Message to post

    Returns:
        True if successful, False otherwise
    """
    return _send_webhook(DISCORD_WEBHOOK_OPS, f"✅ {message}")


def post_err(message: str) -> bool:
    """
    Post error message to Discord errors channel.

    Args:
        message: Error message to post

    Returns:
        True if successful, False otherwise
    """
    return _send_webhook(DISCORD_WEBHOOK_ERRORS, f"❌ {message}")


def post_error(message: str) -> bool:
    """Alias for post_err for backward compatibility."""
    return post_err(message)
