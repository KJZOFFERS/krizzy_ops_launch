from twilio.rest import Client
import os

def send_sms(to_number, body):
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    messaging_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
    client.messages.create(to=to_number, messaging_service_sid=messaging_sid, body=body)
