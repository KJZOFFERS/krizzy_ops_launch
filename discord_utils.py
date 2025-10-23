"""
Discord utilities with retry logic and error handling.
"""
import os
import requests
import json
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from kpi import kpi_push


class DiscordNotifier:
    """Discord webhook notifications with retry logic."""
    
    def __init__(self):
        self.ops_webhook = os.getenv("DISCORD_WEBHOOK_OPS")
        self.errors_webhook = os.getenv("DISCORD_WEBHOOK_ERRORS")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def _send_webhook(self, webhook_url: str, message: str, webhook_type: str) -> bool:
        """Send message to Discord webhook with retry logic."""
        try:
            response = requests.post(
                webhook_url,
                json={"content": message},
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                kpi_push("error", {
                    "error_type": "discord_rate_limit",
                    "message": f"Discord rate limit exceeded for {webhook_type}: {e}"
                })
            elif e.response.status_code in [403, 404]:
                kpi_push("error", {
                    "error_type": "discord_webhook_error",
                    "message": f"Discord webhook {webhook_type} invalid: {e}"
                })
            else:
                kpi_push("error", {
                    "error_type": "discord_http_error",
                    "message": f"Discord {webhook_type} HTTP error: {e}"
                })
            raise
        except Exception as e:
            kpi_push("error", {
                "error_type": "discord_network_error",
                "message": f"Discord {webhook_type} network error: {e}"
            })
            raise
    
    def post_ops(self, message: str) -> bool:
        """Post message to operations Discord channel."""
        if not self.ops_webhook:
            print(f"Discord OPS webhook not configured. Message: {message}")
            return False
        
        try:
            formatted_message = f"✅ {message}"
            return self._send_webhook(self.ops_webhook, formatted_message, "ops")
        except Exception as e:
            print(f"Failed to post to Discord OPS: {e}")
            return False
    
    def post_err(self, message: str) -> bool:
        """Post error message to errors Discord channel."""
        if not self.errors_webhook:
            print(f"Discord ERR webhook not configured. Error: {message}")
            return False
        
        try:
            formatted_message = f"❌ {message}"
            return self._send_webhook(self.errors_webhook, formatted_message, "errors")
        except Exception as e:
            print(f"Failed to post to Discord ERR: {e}")
            return False


# Global Discord notifier instance
discord = DiscordNotifier()


# Convenience functions for backward compatibility
def post_ops(message: str) -> bool:
    """Convenience function for posting to operations channel."""
    return discord.post_ops(message)


def post_error(message: str) -> bool:
    """Convenience function for posting to errors channel."""
    return discord.post_err(message)


def post_err(message: str) -> bool:
    """Alias for post_error for backward compatibility."""
    return discord.post_err(message)
