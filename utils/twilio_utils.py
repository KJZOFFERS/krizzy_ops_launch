import os
from twilio.rest import Client

ACC = os.environ["TWILIO_ACCOUNT_SID"]
TOK = os.environ["TWILIO_AUTH_TOKEN"]
MSG = os.environ["TWILIO_MESSAGING_SERVICE_SID"]

client = Client(ACC, TOK)

def send_sms(to, body):
    return client.messages.create(
        messaging_service_sid=MSG,
        to=to,
        body=body
    )
