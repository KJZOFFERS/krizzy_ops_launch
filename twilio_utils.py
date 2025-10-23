"""Twilio utilities for SMS messaging with content rotation."""

import os
import time
import random
from typing import Optional, List
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException


TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")


_content_templates = [
    "Hi! {message}",
    "Hello! {message}",
    "Hey there! {message}",
    "Greetings! {message}",
]


def _exponential_backoff_with_jitter(
    attempt: int, base_delay: float = 1.0, max_delay: float = 32.0
) -> float:
    """Calculate exponential backoff with jitter."""
    delay = min(base_delay * (2**attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter


def _rotate_content(message: str, attempt: int = 0) -> str:
    """Rotate message content to avoid spam detection."""
    template = _content_templates[attempt % len(_content_templates)]
    return template.format(message=message)


def send_msg(
    to: str, body: str, max_retries: int = 5
) -> Optional[str]:
    """
    Send SMS via Twilio MessagingService with content rotation on 30007.

    Args:
        to: Phone number to send to
        body: Message body
        max_retries: Maximum number of retry attempts

    Returns:
        Message SID on success, None on failure
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_MESSAGING_SERVICE_SID]):
        return None

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    for attempt in range(max_retries):
        try:
            message_body = _rotate_content(body, attempt) if attempt > 0 else body

            message = client.messages.create(
                messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
                body=message_body,
                to=to,
            )
            return message.sid

        except TwilioRestException as e:
            if e.code == 30007:
                delay = _exponential_backoff_with_jitter(attempt)
                time.sleep(delay)
                continue
            elif e.status in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                delay = _exponential_backoff_with_jitter(attempt)
                time.sleep(delay)
                continue
            return None
        except Exception:
            if attempt < max_retries - 1:
                delay = _exponential_backoff_with_jitter(attempt)
                time.sleep(delay)
                continue
            return None

    return None


def send_sms(to: str, body: str) -> Optional[str]:
    """Alias for send_msg for backward compatibility."""
    return send_msg(to, body)
