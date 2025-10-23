from __future__ import annotations

import os
import random
import time
from typing import List

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")

_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 1.0
ROTATE_CONTENT_ERRORS: List[str] = ["30007"]


def _jitter_delay(attempt: int) -> float:
    base = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
    return base + random.uniform(0, 0.5)


def send_msg(to: str, body_variants: List[str]) -> None:
    """Send SMS using Messaging Service.

    Rotates content when Twilio error code 30007 (Filter violation) occurs.
    Retries with backoff + jitter on 429/5xx.
    """
    if not TWILIO_MESSAGING_SERVICE_SID:
        return
    attempt = 0
    variant_index = 0
    while True:
        attempt += 1
        body = body_variants[variant_index % len(body_variants)]
        try:
            _client.messages.create(
                messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
                body=body,
                to=to,
            )
            return
        except TwilioRestException as exc:
            code = str(getattr(exc, "code", ""))
            status = getattr(exc, "status", None)
            if code in ROTATE_CONTENT_ERRORS:
                variant_index += 1
            if status == 429 or (isinstance(status, int) and 500 <= status < 600):
                if attempt >= MAX_RETRIES:
                    return
                time.sleep(_jitter_delay(attempt))
                continue
            return
        except Exception:
            if attempt >= MAX_RETRIES:
                return
            time.sleep(_jitter_delay(attempt))
