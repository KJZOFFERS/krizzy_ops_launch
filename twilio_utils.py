from twilio.rest import Client
import os

def send_sms(to, body):
    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    client.messages.create(
        messaging_service_sid=os.environ["TWILIO_MESSAGING_SERVICE_SID"],
        to=to,
        body=body
    )
