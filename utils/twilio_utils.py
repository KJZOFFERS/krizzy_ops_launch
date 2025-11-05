import os

def send_sms(to: str, body: str):
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    svc = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
    if not (sid and token and svc):
        return None
    try:
        from twilio.rest import Client  # lazy import
    except Exception:
        return None
    client = Client(sid, token)
    msg = client.messages.create(messaging_service_sid=svc, to=to, body=body)
    return {"sid": msg.sid}

