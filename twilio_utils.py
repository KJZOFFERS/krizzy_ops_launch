import logging
import os
import random
from typing import Optional

import backoff
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")

# Content rotation templates for different scenarios
REI_TEMPLATES = [
    "Hi! I saw your property listing and I'm interested in making a cash offer. Are you looking to sell quickly?",
    "Hello! I'm a local investor interested in your property. Would you consider a fast cash sale?",
    "Hi there! I buy houses in your area for cash. Is your property still available?",
    "Hello! I specialize in quick property purchases. Would you like to discuss your property?",
]

GOVCON_TEMPLATES = [
    "Hi! I noticed your upcoming solicitation. Our team specializes in government contracting. Can we discuss?",
    "Hello! We're experienced government contractors interested in your upcoming opportunity. Available to chat?",
    "Hi there! Our company has extensive experience with similar government contracts. Can we connect?",
    "Hello! We'd like to learn more about your solicitation requirements. Are you available for a brief call?",
]

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_MESSAGING_SERVICE_SID]):
    logger.warning("Missing Twilio credentials - SMS functionality will be disabled")
    client = None
else:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


@backoff.on_exception(
    backoff.expo,
    (TwilioRestException,),
    max_tries=3,
    jitter=backoff.random_jitter,
    giveup=lambda e: e.code not in [20429, 30007],  # Rate limit and content filter
)
def send_msg(to: str, body: str, message_type: str = "general") -> Optional[str]:
    """
    Send SMS via Twilio MessagingService with content rotation and error handling.

    Args:
        to: Phone number to send to
        body: Message body (will be rotated if it's a template type)
        message_type: Type of message for template selection (rei, govcon, general)

    Returns:
        Message SID if successful, None if failed
    """
    if not client:
        logger.warning("Twilio client not configured - SMS not sent")
        return None

    # Content rotation for specific message types
    if message_type == "rei" and not body:
        body = random.choice(REI_TEMPLATES)
    elif message_type == "govcon" and not body:
        body = random.choice(GOVCON_TEMPLATES)

    try:
        message = client.messages.create(
            messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID, body=body, to=to
        )

        logger.info(f"SMS sent successfully to {to[:6]}*****: {message.sid}")
        return message.sid

    except TwilioRestException as e:
        if e.code == 30007:  # Content filter violation
            logger.warning(f"Content filter violation for {to[:6]}*****: {e.msg}")
            # Try with a different template
            if message_type in ["rei", "govcon"]:
                templates = REI_TEMPLATES if message_type == "rei" else GOVCON_TEMPLATES
                alternative_body = random.choice([t for t in templates if t != body])
                return send_msg(to, alternative_body, "general")  # Prevent recursion
        elif e.code == 20429:  # Rate limit
            logger.warning(f"Rate limit hit for {to[:6]}*****: {e.msg}")
        else:
            logger.error(f"Twilio error for {to[:6]}*****: {e.code} - {e.msg}")

        return None
    except Exception as e:
        logger.error(f"Unexpected error sending SMS to {to[:6]}*****: {e}")
        return None


def send_rei_message(to: str, custom_body: Optional[str] = None) -> Optional[str]:
    """Send REI-specific message with template rotation."""
    return send_msg(to, custom_body, "rei")


def send_govcon_message(to: str, custom_body: Optional[str] = None) -> Optional[str]:
    """Send GovCon-specific message with template rotation."""
    return send_msg(to, custom_body, "govcon")


def validate_phone_number(phone: str) -> bool:
    """
    Basic phone number validation.

    Args:
        phone: Phone number to validate

    Returns:
        True if valid format, False otherwise
    """
    import re

    # Remove all non-digits
    digits_only = re.sub(r'\D', '', phone)

    # Check if it's a valid US number (10 or 11 digits)
    if len(digits_only) == 10:
        return True
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        return True

    return False


def format_phone_number(phone: str) -> Optional[str]:
    """
    Format phone number for Twilio (E.164 format).

    Args:
        phone: Raw phone number

    Returns:
        Formatted phone number or None if invalid
    """
    import re

    if not phone:
        return None

    # Remove all non-digits
    digits_only = re.sub(r'\D', '', phone)

    # Format to E.164
    if len(digits_only) == 10:
        return f"+1{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        return f"+{digits_only}"

    return None


# Legacy function for backward compatibility
def send_sms(to: str, body: str) -> Optional[str]:
    """Legacy SMS function."""
    return send_msg(to, body)
