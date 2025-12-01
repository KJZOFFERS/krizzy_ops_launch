from twilio.rest import Client
import os

def get_twilio():
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")

    if not sid or not token:
        return None

    try:
        return Client(sid, token)
    except Exception:
        return None
