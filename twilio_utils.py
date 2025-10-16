import os
from twilio.rest import Client

SAFE_MODE = True
client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")

def send_sms(to, body):
    if SAFE_MODE:
        return
    try:
        client.messages.create(messaging_service_sid=SERVICE_SID, body=body, to=to)
    except Exception:
        pass
