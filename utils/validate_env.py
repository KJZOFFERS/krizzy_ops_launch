import os
import logging

logger = logging.getLogger(__name__)

REQUIRED = [
    "AIRTABLE_API_KEY",
    "AIRTABLE_BASE_ID",
    "DISCORD_WEBHOOK_OPS",
    "DISCORD_WEBHOOK_ERRORS",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_MESSAGING_SERVICE_SID",
]

def validate_env():
    missing = [v for v in REQUIRED if v not in os.environ]
    if missing:
        logger.warning(f"Missing env vars (some features may not work): {missing}")
