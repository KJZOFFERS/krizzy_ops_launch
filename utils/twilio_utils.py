import os
from twilio.rest import Client

def send_sms(to, body):
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    svc = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
    Client(sid, token).messages.create(messaging_service_sid=svc, to=to, body=body)
