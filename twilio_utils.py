"""
Twilio utilities with content rotation and error handling.
"""
import os
import random
from typing import List, Optional, Tuple
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from kpi import kpi_push


class TwilioMessenger:
    """Twilio SMS messaging with content rotation and error handling."""
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
        self.safe_mode = os.getenv("TWILIO_SAFE_MODE", "true").lower() == "true"
        
        if not all([self.account_sid, self.auth_token, self.messaging_service_sid]):
            raise ValueError("TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_MESSAGING_SERVICE_SID must be set")
        
        self.client = Client(self.account_sid, self.auth_token)
        
        # Content rotation templates to avoid 30007 error
        self.content_templates = [
            "New opportunity available: {title} - Due: {due_date}",
            "Government contract alert: {title} - Response due: {due_date}",
            "Bid opportunity: {title} - Deadline: {due_date}",
            "Contract solicitation: {title} - Due: {due_date}",
            "Procurement alert: {title} - Response deadline: {due_date}",
            "Government bid: {title} - Due date: {due_date}",
            "Solicitation notice: {title} - Deadline: {due_date}",
            "Contract opportunity: {title} - Due: {due_date}"
        ]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TwilioException, Exception))
    )
    def _send_message(self, to: str, body: str) -> Tuple[bool, str]:
        """Send SMS message with retry logic."""
        try:
            message = self.client.messages.create(
                messaging_service_sid=self.messaging_service_sid,
                body=body,
                to=to
            )
            return True, message.sid
        except TwilioException as e:
            if "30007" in str(e):
                kpi_push("error", {
                    "error_type": "twilio_content_error",
                    "message": f"Twilio content rotation needed (30007): {e}",
                    "to": to
                })
            elif "21211" in str(e):
                kpi_push("error", {
                    "error_type": "twilio_invalid_number",
                    "message": f"Invalid phone number: {e}",
                    "to": to
                })
            elif "21610" in str(e):
                kpi_push("error", {
                    "error_type": "twilio_opt_out",
                    "message": f"Number opted out: {e}",
                    "to": to
                })
            else:
                kpi_push("error", {
                    "error_type": "twilio_error",
                    "message": f"Twilio error: {e}",
                    "to": to
                })
            raise
    
    def _rotate_content(self, base_content: str) -> str:
        """Rotate content to avoid 30007 error."""
        # Add random variation to content
        variations = [
            f"📋 {base_content}",
            f"🔔 {base_content}",
            f"📢 {base_content}",
            f"⚡ {base_content}",
            f"🎯 {base_content}",
            f"💼 {base_content}",
            f"📄 {base_content}",
            f"🏛️ {base_content}"
        ]
        return random.choice(variations)
    
    def send_msg(self, to: str, title: str, due_date: str, 
                custom_content: Optional[str] = None) -> Tuple[bool, str]:
        """
        Send SMS message with content rotation.
        
        Args:
            to: Phone number to send to
            title: Opportunity title
            due_date: Due date
            custom_content: Custom message content (optional)
        
        Returns:
            Tuple of (success: bool, message_sid: str)
        """
        if self.safe_mode:
            print(f"SAFE MODE: Would send SMS to {to}: {title} - Due: {due_date}")
            return True, "safe_mode"
        
        try:
            if custom_content:
                body = custom_content
            else:
                # Use template with content rotation
                template = random.choice(self.content_templates)
                body = template.format(title=title, due_date=due_date)
            
            # Rotate content to avoid 30007
            body = self._rotate_content(body)
            
            success, message_sid = self._send_message(to, body)
            
            if success:
                kpi_push("cycle_end", {
                    "engine": "twilio",
                    "count": 1,
                    "message": f"SMS sent to {to}"
                })
            
            return success, message_sid
            
        except Exception as e:
            kpi_push("error", {
                "error_type": "twilio_send_error",
                "message": f"Failed to send SMS to {to}: {e}",
                "title": title
            })
            return False, str(e)
    
    def send_bulk_messages(self, recipients: List[Tuple[str, str, str]], 
                          custom_content: Optional[str] = None) -> List[Tuple[bool, str]]:
        """
        Send bulk SMS messages with content rotation.
        
        Args:
            recipients: List of (phone, title, due_date) tuples
            custom_content: Custom message content (optional)
        
        Returns:
            List of (success: bool, message_sid: str) tuples
        """
        results = []
        
        for phone, title, due_date in recipients:
            success, message_sid = self.send_msg(phone, title, due_date, custom_content)
            results.append((success, message_sid))
            
            # Add small delay between messages to avoid rate limits
            import time
            time.sleep(0.5)
        
        return results


# Global Twilio messenger instance (lazy initialization)
_twilio_instance = None

def get_twilio_messenger():
    """Get or create Twilio messenger instance."""
    global _twilio_instance
    if _twilio_instance is None:
        _twilio_instance = TwilioMessenger()
    return _twilio_instance

# For backward compatibility
class TwilioMessengerProxy:
    def __getattr__(self, name):
        return getattr(get_twilio_messenger(), name)

twilio = TwilioMessengerProxy()


# Convenience functions for backward compatibility
def send_sms(to: str, body: str) -> Tuple[bool, str]:
    """Legacy function - use send_msg for new code."""
    return twilio.send_msg(to, "Notification", "N/A", body)


def send_msg(to: str, title: str, due_date: str, 
            custom_content: Optional[str] = None) -> Tuple[bool, str]:
    """Convenience function for sending messages."""
    return twilio.send_msg(to, title, due_date, custom_content)
