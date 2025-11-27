# src/ops/preflight.py

import os
from typing import Dict, Any
from datetime import datetime, timezone

from .ops_notify import send_health, send_crack
from ..common.airtable_client import AirtableClient
from ..common.http_utils import get_json_retry


def run_preflight() -> bool:
    """
    Run pre-flight checks on all critical systems.
    Returns True if all checks pass, False otherwise.
    Sends HEALTH snapshot + CRACKs for any failing subsystems.
    """
    print(f"[PREFLIGHT] Starting checks at {datetime.now(timezone.utc).isoformat()}")
    
    checks: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "env_vars": True,
        "airtable_auth": False,
        "airtable_schema": False,
        "discord_webhooks": False,
        "sam_api": None,
    }
    
    # 1. Check required env vars
    required_vars = [
        "AIRTABLE_API_KEY",
        "AIRTABLE_BASE_ID",
        "DISCORD_WEBHOOK_OPS",
    ]
    missing_vars = [v for v in required_vars if not os.getenv(v, "").strip()]
    if missing_vars:
        checks["env_vars"] = False
        checks["missing_vars"] = missing_vars
        send_crack("preflight", f"Missing required env vars: {missing_vars}")
        print(f"[PREFLIGHT] ❌ Missing env vars: {missing_vars}")
    else:
        print("[PREFLIGHT] ✅ Required env vars present")
    
    # 2. Check Airtable auth + Meta API
    try:
        client = AirtableClient()
        tables = client.get_tables(use_cache=False)
        checks["airtable_auth"] = True
        checks["airtable_tables_count"] = len(tables)
        print(f"[PREFLIGHT] ✅ Airtable auth OK, found {len(tables)} tables")
        
        # 3. Verify critical tables exist
        table_names = [t.get("name") for t in tables]
        required_tables = [
            "Leads_REI",
            "Buyers",
            "GovCon Opportunities",
            "KPI_Log",
            "Cracks_Tracker",
            "SMS_Queue",
            "REI_Matches",
        ]
        missing_tables = [t for t in required_tables if t not in table_names]
        if missing_tables:
            checks["airtable_schema"] = False
            checks["missing_tables"] = missing_tables
            send_crack("preflight", f"Missing Airtable tables: {missing_tables}")
            print(f"[PREFLIGHT] ❌ Missing tables: {missing_tables}")
        else:
            checks["airtable_schema"] = True
            print(f"[PREFLIGHT] ✅ All required tables exist")
    
    except Exception as e:
        checks["airtable_auth"] = False
        checks["airtable_error"] = str(e)
        send_crack("preflight", f"Airtable check failed: {e}")
        print(f"[PREFLIGHT] ❌ Airtable check failed: {e}")
    
    # 4. Check Discord webhooks
    webhook_ops = os.getenv("DISCORD_WEBHOOK_OPS", "").strip()
    if webhook_ops and webhook_ops.startswith("https://discord"):
        checks["discord_webhooks"] = True
        print("[PREFLIGHT] ✅ Discord webhooks configured")
    else:
        checks["discord_webhooks"] = False
        print("[PREFLIGHT] ⚠️  Discord webhooks not configured")
    
    # 5. Check SAM.gov API (optional)
    sam_api = os.getenv("SAM_SEARCH_API", "").strip()
    if sam_api:
        try:
            status, data = get_json_retry(sam_api, max_retries=2, timeout=15)
            if status == 200:
                checks["sam_api"] = "ok"
                print("[PREFLIGHT] ✅ SAM.gov API reachable")
            else:
                checks["sam_api"] = f"error_{status}"
                send_crack("preflight", f"SAM.gov API returned status {status}")
                print(f"[PREFLIGHT] ⚠️  SAM.gov API status {status}")
        except Exception as e:
            checks["sam_api"] = "unreachable"
            send_crack("preflight", f"SAM.gov API unreachable: {e}")
            print(f"[PREFLIGHT] ⚠️  SAM.gov API unreachable: {e}")
    else:
        checks["sam_api"] = "disabled"
        print("[PREFLIGHT] ⚠️  SAM.gov API not configured")
    
    # Send health snapshot
    all_critical_pass = (
        checks["env_vars"]
        and checks["airtable_auth"]
        and checks["airtable_schema"]
    )
    
    summary = "ALL SYSTEMS GO" if all_critical_pass else "DEGRADED"
    send_health(summary, checks)
    
    print(f"[PREFLIGHT] Summary: {summary}")
    return all_critical_pass
