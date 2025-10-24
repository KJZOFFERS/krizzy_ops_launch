from twilio.rest import Client
import os

def send_sms(to, body):
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    client.messages.create(
        to=to,
        from_=os.getenv("TWILIO_MESSAGING_SERVICE_SID"),
        body=body
    )
