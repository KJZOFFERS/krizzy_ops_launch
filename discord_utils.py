import os
import requests
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPS_WEBHOOK = os.getenv("DISCORD_WEBHOOK_OPS")
ERROR_WEBHOOK = os.getenv("DISCORD_WEBHOOK_ERRORS")

class DiscordError(Exception):
    """Custom exception for Discord operations"""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((requests.exceptions.RequestException, DiscordError))
)
def post_ops(msg: str) -> bool:
    """
    Post message to Discord ops channel with retry logic.
    
    Args:
        msg: Message to post
        
    Returns:
        True if successful, False otherwise
    """
    if not OPS_WEBHOOK:
        logger.warning("DISCORD_WEBHOOK_OPS not configured")
        return False
    
    try:
        response = requests.post(
            OPS_WEBHOOK,
            json={"content": f"✅ {msg}"},
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Discord ops message sent: {msg[:50]}...")
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("Discord rate limited, will retry")
            raise
        logger.error(f"Discord ops HTTP error: {e}")
        raise DiscordError(f"HTTP error posting to ops: {e}")
    except Exception as e:
        logger.error(f"Discord ops post failed: {e}")
        raise DiscordError(f"Failed to post ops message: {e}")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((requests.exceptions.RequestException, DiscordError))
)
def post_error(msg: str) -> bool:
    """
    Post error message to Discord errors channel with retry logic.
    
    Args:
        msg: Error message to post
        
    Returns:
        True if successful, False otherwise
    """
    if not ERROR_WEBHOOK:
        logger.warning("DISCORD_WEBHOOK_ERRORS not configured")
        return False
    
    try:
        response = requests.post(
            ERROR_WEBHOOK,
            json={"content": f"❌ {msg}"},
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Discord error message sent: {msg[:50]}...")
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("Discord rate limited, will retry")
            raise
        logger.error(f"Discord error HTTP error: {e}")
        raise DiscordError(f"HTTP error posting to errors: {e}")
    except Exception as e:
        logger.error(f"Discord error post failed: {e}")
        raise DiscordError(f"Failed to post error message: {e}")

def post_err(msg: str) -> bool:
    """Alias for post_error for backward compatibility"""
    return post_error(msg)
