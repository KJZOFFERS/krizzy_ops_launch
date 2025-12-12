import os
from twilio.rest import Client

ACC = os.getenv("TWILIO_ACCOUNT_SID", "")
TOK = os.getenv("TWILIO_AUTH_TOKEN", "")
MSG = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "")

client = Client(ACC, TOK) if ACC and TOK else None

def send_sms(to, body):
    if not client:
        raise RuntimeError("Twilio client not configured (missing env vars)")
    return client.messages.create(
        messaging_service_sid=MSG,
        to=to,
        body=body
    )
