import os
import logging
import random
from typing import Optional, List, Dict
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")

# Content rotation for 30007 error handling
MESSAGE_TEMPLATES = [
    "🏠 New REI opportunity: {property_address} - {price} | Contact: {contact_info}",
    "💰 Investment Alert: {property_address} | ARV: {arv} | Agent: {agent} | {contact_info}",
    "📈 REI Lead: {property_address} | Price: {price} | {contact_info} | View: {source_url}",
    "🔑 Property Deal: {property_address} | {price} | Contact: {contact_info}",
    "💎 Investment Opportunity: {property_address} | {price} | {contact_info}"
]

class TwilioError(Exception):
    """Custom exception for Twilio operations"""
    pass

def _get_client() -> Client:
    """Get Twilio client instance"""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise TwilioError("Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN")
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((TwilioException, TwilioError))
)
def send_msg(to: str, body: str, content_rotation: bool = True) -> bool:
    """
    Send SMS message via Twilio with retry logic and content rotation.
    
    Args:
        to: Phone number to send to
        body: Message body
        content_rotation: Whether to use content rotation for 30007 errors
        
    Returns:
        True if successful, False otherwise
    """
    if not TWILIO_MESSAGING_SERVICE_SID:
        logger.warning("TWILIO_MESSAGING_SERVICE_SID not configured")
        return False
    
    try:
        client = _get_client()
        
        # Use content rotation if enabled
        if content_rotation and len(body) > 50:
            # Select random template for content rotation
            template = random.choice(MESSAGE_TEMPLATES)
            # Extract key info from body for template substitution
            body = template.format(
                property_address="Property",
                price="Price",
                contact_info="Contact",
                arv="ARV",
                agent="Agent",
                source_url="URL"
            )
        
        message = client.messages.create(
            messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
            body=body,
            to=to
        )
        
        logger.info(f"SMS sent to {to}: {message.sid}")
        return True
        
    except TwilioException as e:
        if e.code == 30007:  # Content filtering error
            logger.warning(f"Content filtered (30007) for {to}, trying rotation")
            if content_rotation:
                # Try again with different content
                return send_msg(to, "New REI opportunity available. Contact for details.", False)
            else:
                logger.error(f"Content still filtered after rotation for {to}")
                return False
        elif e.code == 429:  # Rate limit
            logger.warning("Twilio rate limited, will retry")
            raise
        else:
            logger.error(f"Twilio error {e.code}: {e.msg}")
            raise TwilioError(f"Twilio error {e.code}: {e.msg}")
    except Exception as e:
        logger.error(f"Twilio send failed: {e}")
        raise TwilioError(f"Failed to send SMS: {e}")

def send_sms(to: str, body: str) -> bool:
    """Legacy function for backward compatibility"""
    return send_msg(to, body)

def send_bulk_sms(recipients: List[str], body: str) -> Dict[str, bool]:
    """
    Send SMS to multiple recipients with individual error handling.
    
    Args:
        recipients: List of phone numbers
        body: Message body
        
    Returns:
        Dict mapping phone numbers to success status
    """
    results = {}
    for recipient in recipients:
        try:
            results[recipient] = send_msg(recipient, body)
        except Exception as e:
            logger.error(f"Failed to send to {recipient}: {e}")
            results[recipient] = False
    return results
