import logging
import os
from datetime import datetime

import backoff
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS")
DISCORD_WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS")

if not DISCORD_WEBHOOK_OPS:
    logger.warning("DISCORD_WEBHOOK_OPS not configured")
if not DISCORD_WEBHOOK_ERRORS:
    logger.warning("DISCORD_WEBHOOK_ERRORS not configured")


@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException,),
    max_tries=3,
    jitter=backoff.random_jitter,
    giveup=lambda e: e.response is not None and e.response.status_code < 500,
)
def _send_discord_message(webhook_url: str, content: str, username: str = "KRIZZY-OPS") -> bool:
    """
    Send message to Discord webhook with backoff and error handling.

    Args:
        webhook_url: Discord webhook URL
        content: Message content
        username: Bot username

    Returns:
        True if successful, False otherwise
    """
    if not webhook_url:
        logger.warning("Discord webhook URL not provided")
        return False

    try:
        payload = {
            "content": content,
            "username": username,
            "avatar_url": "https://cdn.discordapp.com/emojis/1234567890.png",  # Optional bot avatar
        }

        response = requests.post(
            webhook_url, json=payload, timeout=10, headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        logger.info(f"Discord message sent successfully: {content[:50]}...")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Discord message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}, body: {e.response.text}")
        return False


def post_ops(msg: str) -> bool:
    """
    Post operational message to Discord ops channel.

    Args:
        msg: Message to send

    Returns:
        True if successful, False otherwise
    """
    timestamp = datetime.utcnow().strftime("%H:%M:%S UTC")
    formatted_msg = f"✅ **[{timestamp}]** {msg}"
    return _send_discord_message(DISCORD_WEBHOOK_OPS, formatted_msg)


def post_error(msg: str) -> bool:
    """
    Post error message to Discord errors channel.

    Args:
        msg: Error message to send

    Returns:
        True if successful, False otherwise
    """
    timestamp = datetime.utcnow().strftime("%H:%M:%S UTC")
    formatted_msg = f"❌ **[{timestamp}]** {msg}"
    return _send_discord_message(DISCORD_WEBHOOK_ERRORS, formatted_msg)


def post_kpi(event: str, data: dict) -> bool:
    """
    Post KPI event to Discord ops channel.

    Args:
        event: KPI event name
        data: KPI data

    Returns:
        True if successful, False otherwise
    """
    timestamp = datetime.utcnow().strftime("%H:%M:%S UTC")
    formatted_msg = f"📊 **[{timestamp}]** KPI: {event} - {data}"
    return _send_discord_message(DISCORD_WEBHOOK_OPS, formatted_msg)
