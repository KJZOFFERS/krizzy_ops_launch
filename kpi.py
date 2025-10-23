"""
KPI logging system for KRIZZY OPS.
Tracks all events and metrics for monitoring and alerting.
"""
import os
import json
import time
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class KPILogger:
    """Centralized KPI logging with retry logic and error handling."""
    
    def __init__(self):
        self.airtable_api_key = os.getenv("AIRTABLE_API_KEY")
        self.airtable_base_id = os.getenv("AIRTABLE_BASE_ID")
        self.discord_webhook_ops = os.getenv("DISCORD_WEBHOOK_OPS")
        self.discord_webhook_errors = os.getenv("DISCORD_WEBHOOK_ERRORS")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, Exception))
    )
    def _post_to_airtable(self, table_name: str, record: Dict[str, Any]) -> bool:
        """Post record to Airtable with retry logic."""
        try:
            from pyairtable import Table
            table = Table(self.airtable_api_key, self.airtable_base_id, table_name)
            table.create(record)
            return True
        except Exception as e:
            print(f"Failed to post to Airtable {table_name}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def _post_to_discord(self, webhook_url: str, message: str) -> bool:
        """Post message to Discord with retry logic."""
        try:
            response = requests.post(
                webhook_url,
                json={"content": message},
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to post to Discord: {e}")
            raise
    
    def kpi_push(self, event: str, data: Dict[str, Any]) -> None:
        """
        Push KPI event to Airtable and Discord.
        
        Args:
            event: Event name (e.g., 'boot', 'cycle_start', 'cycle_end', 'error')
            data: Event data dictionary
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Create KPI record
        kpi_record = {
            "Event": event,
            "Timestamp": timestamp,
            "Data": json.dumps(data),
            "Status": "success" if event != "error" else "error"
        }
        
        # Add event-specific fields
        if event == "boot":
            kpi_record["System"] = "KRIZZY_OPS"
            kpi_record["Version"] = "3.0.0"
        elif event in ["cycle_start", "cycle_end"]:
            kpi_record["Engine"] = data.get("engine", "unknown")
            kpi_record["Records_Processed"] = data.get("count", 0)
        elif event == "error":
            kpi_record["Error_Type"] = data.get("error_type", "unknown")
            kpi_record["Error_Message"] = data.get("message", "unknown")
        
        # Post to Airtable (non-blocking)
        try:
            self._post_to_airtable("KPI_Log", kpi_record)
        except Exception as e:
            print(f"KPI Airtable post failed: {e}")
        
        # Post to Discord based on event type
        try:
            if event == "boot":
                message = f"🚀 KRIZZY OPS v3.0.0 started at {timestamp}"
                if self.discord_webhook_ops:
                    self._post_to_discord(self.discord_webhook_ops, message)
            elif event == "cycle_start":
                engine = data.get("engine", "unknown")
                message = f"🔄 {engine.upper()} cycle started at {timestamp}"
                if self.discord_webhook_ops:
                    self._post_to_discord(self.discord_webhook_ops, message)
            elif event == "cycle_end":
                engine = data.get("engine", "unknown")
                count = data.get("count", 0)
                message = f"✅ {engine.upper()} cycle completed: {count} records processed at {timestamp}"
                if self.discord_webhook_ops:
                    self._post_to_discord(self.discord_webhook_ops, message)
            elif event == "error":
                error_type = data.get("error_type", "unknown")
                error_msg = data.get("message", "unknown")
                message = f"❌ ERROR [{error_type}]: {error_msg} at {timestamp}"
                if self.discord_webhook_errors:
                    self._post_to_discord(self.discord_webhook_errors, message)
        except Exception as e:
            print(f"KPI Discord post failed: {e}")


# Global KPI logger instance
kpi = KPILogger()


def kpi_push(event: str, data: Dict[str, Any]) -> None:
    """Convenience function for KPI logging."""
    kpi.kpi_push(event, data)