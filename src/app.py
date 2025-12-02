import os
from fastapi import FastAPI

app = FastAPI()

# ================== TWILIO CONFIG (OPTIONAL) ==================

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")  # e.g. "+1617XXXXXXX"

TWILIO_ENABLED = bool(
    TWILIO_ACCOUNT_SID
    and TWILIO_AUTH_TOKEN
    and (TWILIO_MESSAGING_SERVICE_SID or TWILIO_FROM_NUMBER)
)

try:
    from twilio.rest import Client  # type: ignore
except ImportError:
    Client = None  # type: ignore[assignment]
    TWILIO_ENABLED = False

if TWILIO_ENABLED and Client is not None:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    twilio_client = None


def send_sms(to: str, body: str) -> None:
    """
    Safe Twilio wrapper.
    - If Twilio is not configured or library missing: logs and returns.
    - If configured: sends real SMS.
    """
    if not TWILIO_ENABLED or twilio_client is None:
        print(f"[TWILIO_DISABLED] SMS to={to} body={body}")
        return

    kwargs = {"to": to, "body": body}
    if TWILIO_MESSAGING_SERVICE_SID:
        kwargs["messaging_service_sid"] = TWILIO_MESSAGING_SERVICE_SID
    elif TWILIO_FROM_NUMBER:
        kwargs["from_"] = TWILIO_FROM_NUMBER
    else:
        print("[TWILIO_DISABLED] No FROM configured.")
        return

    twilio_client.messages.create(**kwargs)

# ================== END TWILIO CONFIG ==================
