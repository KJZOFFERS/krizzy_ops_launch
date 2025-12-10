import requests
from typing import Optional
from app_v2 import config
from app_v2.utils.logger import get_logger

logger = get_logger(__name__)


def post_to_discord(webhook_url: str, message: str) -> bool:
    """Post message to Discord webhook"""
    try:
        payload = {"content": message[:2000]}  # Discord limit
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Discord webhook failed: {e}")
        return False


def post_ops(message: str) -> bool:
    """Post to operations webhook"""
    if not config.DISCORD_WEBHOOK_OPS:
        return False
    return post_to_discord(config.DISCORD_WEBHOOK_OPS, message)


def post_error(message: str) -> bool:
    """Post to errors webhook"""
    if not config.DISCORD_WEBHOOK_ERRORS:
        return False
    return post_to_discord(config.DISCORD_WEBHOOK_ERRORS, message)


def post_deal_alert(deal_address: str, spread: float, arv: float, asking: float) -> bool:
    """Post high-value deal alert"""
    message = (
        f"🔥 **HIGH-VALUE DEAL ALERT**\n"
        f"Address: {deal_address}\n"
        f"Spread: ${spread:,.0f}\n"
        f"ARV: ${arv:,.0f}\n"
        f"Asking: ${asking:,.0f}"
    )
    return post_ops(message)


def post_system_alert(alert_type: str, details: str) -> bool:
    """Post system alert"""
    message = f"⚠️ **SYSTEM ALERT: {alert_type}**\n{details}"
    return post_error(message)
