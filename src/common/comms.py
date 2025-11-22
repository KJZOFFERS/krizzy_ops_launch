"""Communication utilities - Discord webhooks + Twilio SMS"""
import os
import requests
from datetime import datetime, timezone
from typing import Optional

DISCORD_WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS", "")
DISCORD_WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS", "") or DISCORD_WEBHOOK_OPS

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "")


def notify_ops(message: str) -> bool:
    """Send notification to ops channel"""
    if not DISCORD_WEBHOOK_OPS:
        return False
    try:
        r = requests.post(DISCORD_WEBHOOK_OPS, json={"content": message[:1900]}, timeout=8)
        return r.status_code in (200, 204)
    except Exception:
        return False


def notify_error(message: str) -> bool:
    """Send notification to errors channel"""
    if not DISCORD_WEBHOOK_ERRORS:
        return False
    try:
        r = requests.post(DISCORD_WEBHOOK_ERRORS, json={"content": message[:1900]}, timeout=8)
        return r.status_code in (200, 204)
    except Exception:
        return False


def log_crack(service: str, error: str, client=None) -> None:
    """Log crack to Cracks_Tracker and notify errors channel"""
    ts = datetime.now(timezone.utc).isoformat()
    notify_error(f"❌ CRACK | {service} | {error} | {ts}")
    if client:
        try:
            client.log_crack(service, error)
        except Exception:
            pass


def twilio_available() -> bool:
    """Check if Twilio is configured"""
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_MESSAGING_SERVICE_SID)


def twilio_send(to_phone: str, message: str) -> bool:
    """Send SMS via Twilio (returns False if not configured)"""
    if not twilio_available():
        return False
    
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
            to=to_phone,
            body=message
        )
        return bool(msg.sid)
    except Exception as e:
        print(f"[TWILIO] Send failed: {e}")
        return False
