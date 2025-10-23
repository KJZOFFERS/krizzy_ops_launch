"""
Health check utilities for KRIZZY OPS.
"""
import time
import datetime
import requests
import os
from typing import Dict, Any


def check_airtable_health() -> Dict[str, Any]:
    """Check Airtable connectivity."""
    try:
        from pyairtable import Table
        api_key = os.getenv("AIRTABLE_API_KEY")
        base_id = os.getenv("AIRTABLE_BASE_ID")
        
        if not api_key or not base_id:
            return {"status": "error", "message": "Missing Airtable credentials"}
        
        table = Table(api_key, base_id, "KPI_Log")
        # Try to fetch one record to test connectivity
        records = table.all(max_records=1)
        return {"status": "ok", "message": "Airtable connected"}
    except Exception as e:
        return {"status": "error", "message": f"Airtable error: {e}"}


def check_discord_health() -> Dict[str, Any]:
    """Check Discord webhook connectivity."""
    try:
        ops_webhook = os.getenv("DISCORD_WEBHOOK_OPS")
        if not ops_webhook:
            return {"status": "warning", "message": "Discord OPS webhook not configured"}
        
        # Test webhook with a simple request
        response = requests.post(
            ops_webhook,
            json={"content": "🔍 Health check test"},
            timeout=5
        )
        response.raise_for_status()
        return {"status": "ok", "message": "Discord webhooks working"}
    except Exception as e:
        return {"status": "error", "message": f"Discord error: {e}"}


def check_twilio_health() -> Dict[str, Any]:
    """Check Twilio connectivity."""
    try:
        from twilio.rest import Client
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if not account_sid or not auth_token:
            return {"status": "error", "message": "Missing Twilio credentials"}
        
        client = Client(account_sid, auth_token)
        # Test by fetching account info
        account = client.api.accounts(account_sid).fetch()
        return {"status": "ok", "message": f"Twilio connected (Account: {account.friendly_name})"}
    except Exception as e:
        return {"status": "error", "message": f"Twilio error: {e}"}


def check_sam_health() -> Dict[str, Any]:
    """Check SAM.gov API connectivity."""
    try:
        sam_api = os.getenv("SAM_SEARCH_API")
        if not sam_api:
            return {"status": "error", "message": "SAM_SEARCH_API not configured"}
        
        # Test with a simple request
        response = requests.get(sam_api, params={"limit": 1}, timeout=10)
        response.raise_for_status()
        return {"status": "ok", "message": "SAM.gov API accessible"}
    except Exception as e:
        return {"status": "error", "message": f"SAM.gov error: {e}"}


def check_fpds_health() -> Dict[str, Any]:
    """Check FPDS ATOM feed connectivity."""
    try:
        fpds_feed = os.getenv("FPDS_ATOM_FEED")
        if not fpds_feed:
            return {"status": "error", "message": "FPDS_ATOM_FEED not configured"}
        
        # Test with a simple request
        response = requests.get(fpds_feed, timeout=10)
        response.raise_for_status()
        return {"status": "ok", "message": "FPDS ATOM feed accessible"}
    except Exception as e:
        return {"status": "error", "message": f"FPDS error: {e}"}


def comprehensive_health_check() -> Dict[str, Any]:
    """Run comprehensive health check on all services."""
    checks = {
        "airtable": check_airtable_health(),
        "discord": check_discord_health(),
        "twilio": check_twilio_health(),
        "sam": check_sam_health(),
        "fpds": check_fpds_health()
    }
    
    # Determine overall status
    statuses = [check["status"] for check in checks.values()]
    if "error" in statuses:
        overall_status = "error"
    elif "warning" in statuses:
        overall_status = "warning"
    else:
        overall_status = "ok"
    
    return {
        "status": overall_status,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "checks": checks,
        "uptime_seconds": time.time() - os.getenv("STARTUP_TIME", time.time())
    }
