# src/common/twilio_client.py
import os
import httpx
from base64 import b64encode

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SERVICE = os.getenv("TWILIO_MESSAGING_SERVICE_SID")


class TwilioClient:
    def __init__(self):
        if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_SERVICE:
            raise RuntimeError("Missing Twilio env vars.")

        token = f"{TWILIO_SID}:{TWILIO_TOKEN}"
        self.auth_header = b64encode(token.encode()).decode()
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}"

    async def send_sms(self, to, body):
        data = {
            "MessagingServiceSid": TWILIO_SERVICE,
            "To": to,
            "Body": body
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/Messages.json",
                data=data,
                headers={"Authorization": f"Basic {self.auth_header}"}
            )
            r.raise_for_status()
            return r.json()
