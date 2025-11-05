# FILE: twilio_utils.py
import os

def send_sms(to_phone: str, body: str) -> dict:
    """
    Lazy import Twilio to avoid boot-time dependency if unused.
    Requires env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM
    """
    from twilio.rest import Client  # type: ignore
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    tok = os.getenv("TWILIO_AUTH_TOKEN")
    from_num = os.getenv("TWILIO_FROM")
    if not (sid and tok and from_num):
        raise RuntimeError("Twilio env vars missing")
    cli = Client(sid, tok)
    msg = cli.messages.create(to=to_phone, from_=from_num, body=body)
    return {"sid": msg.sid, "status": msg.status}
