from typing import Any, Dict


def repair_code(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interpret error messages and return concrete repair actions for V2.

    Input:
      - error: str (error message)
      - context: optional metadata (engine name, table, etc.)

    Returns:
      - category: error classification
      - hint: human-readable explanation
      - suggested_action: concrete next step
      - auto_fix_available: bool (if V2 can auto-repair)
    """
    error = str(payload.get("error", "")).lower()
    context = payload.get("context", {})

    # Schema/field mismatch errors
    if any(term in error for term in ["unprocessable entity", "422", "invalid field", "unknown field"]):
        return {
            "category": "schema_mismatch",
            "hint": (
                "Airtable field name mismatch. Check that payload keys match exact field names in Airtable. "
                "Common issues: case sensitivity, underscores vs spaces, field renamed in Airtable."
            ),
            "suggested_action": "inspect_schema_map_and_update_field_mapping",
            "auto_fix_available": False,
            "debug_steps": [
                "1. Check app_v2/llm_control/schema_map.py for correct field names",
                "2. Compare payload keys against Airtable schema",
                "3. Update engine to use correct field names",
                "4. Retry operation",
            ],
        }

    # Permission errors
    if any(term in error for term in ["invalid_permissions", "403", "forbidden", "not authorized"]):
        return {
            "category": "permissions",
            "hint": (
                "Airtable API permission issue. Verify Personal Access Token (PAT) has correct scopes "
                "and access to the base."
            ),
            "suggested_action": "verify_airtable_pat_scopes_and_base_access",
            "auto_fix_available": False,
            "debug_steps": [
                "1. Go to Airtable → Account → Developer Hub → Personal access tokens",
                "2. Verify token has these scopes: data.records:read, data.records:write, schema.bases:read",
                "3. Verify token has access to KRIZZY_OPS_CRM base",
                "4. Regenerate token if needed and update AIRTABLE_API_KEY env var",
            ],
        }

    # Network/connection errors
    if any(term in error for term in ["connection", "timeout", "network", "unreachable"]):
        return {
            "category": "network",
            "hint": (
                "Network connectivity issue. Could be temporary outage, DNS problem, or firewall blocking."
            ),
            "suggested_action": "apply_retry_with_exponential_backoff",
            "auto_fix_available": True,
            "debug_steps": [
                "1. Check internet connectivity",
                "2. Verify Airtable API is accessible (https://api.airtable.com/)",
                "3. Check for firewall/proxy blocking",
                "4. V2 will auto-retry with backoff",
            ],
        }

    # Rate limiting
    if any(term in error for term in ["429", "rate limit", "too many requests"]):
        return {
            "category": "rate_limit",
            "hint": (
                "Airtable rate limit exceeded (5 requests/second per base). "
                "V2 needs to slow down API calls."
            ),
            "suggested_action": "apply_rate_limiting_backoff",
            "auto_fix_available": True,
            "debug_steps": [
                "1. V2 will automatically backoff for 30 seconds",
                "2. Consider batching operations",
                "3. Increase engine intervals in config.py",
            ],
        }

    # Discord webhook errors
    if any(term in error for term in ["discord", "webhook"]):
        return {
            "category": "discord_webhook",
            "hint": "Discord webhook delivery failed. Non-critical - system continues.",
            "suggested_action": "verify_discord_webhook_url",
            "auto_fix_available": False,
            "debug_steps": [
                "1. Check DISCORD_WEBHOOK_OPS and DISCORD_WEBHOOK_ERRORS env vars",
                "2. Test webhooks manually with curl",
                "3. Verify webhooks not rate-limited by Discord",
            ],
        }

    # Twilio errors
    if any(term in error for term in ["twilio", "30007", "sms delivery"]):
        return {
            "category": "twilio_delivery",
            "hint": (
                "Twilio delivery issue. Could be carrier filtering, compliance violation, or bad number."
            ),
            "suggested_action": "review_twilio_error_code_and_adjust_messaging",
            "auto_fix_available": False,
            "debug_steps": [
                "1. Check Twilio logs for specific error code",
                "2. If 30007: Review message content for spam triggers",
                "3. If 30008: Verify number formatting",
                "4. Rotate message templates in outbound_control_engine",
            ],
        }

    # Gmail API errors
    if any(term in error for term in ["gmail", "google api", "oauth"]):
        return {
            "category": "gmail_api",
            "hint": "Gmail API authentication or quota issue.",
            "suggested_action": "refresh_gmail_oauth_token",
            "auto_fix_available": False,
            "debug_steps": [
                "1. Check GMAIL_CREDENTIALS_JSON and GMAIL_TOKEN_JSON env vars",
                "2. Verify OAuth2 token hasn't expired",
                "3. Re-authenticate if needed",
                "4. Check Gmail API quota in Google Cloud Console",
            ],
        }

    # Thread/concurrency errors
    if any(term in error for term in ["thread", "deadlock", "lock"]):
        return {
            "category": "concurrency",
            "hint": "Thread synchronization issue. Possible deadlock or race condition.",
            "suggested_action": "review_thread_locks_and_restart_engine",
            "auto_fix_available": True,
            "debug_steps": [
                "1. Thread supervisor will auto-restart crashed engine",
                "2. Check logs for lock acquisition patterns",
                "3. If persistent, review engine code for lock ordering",
            ],
        }

    # Unknown error
    return {
        "category": "unknown",
        "hint": f"Unhandled error pattern. Full error: {payload.get('error', 'N/A')}",
        "suggested_action": "manual_review_and_update_dev_agent",
        "auto_fix_available": False,
        "debug_steps": [
            "1. Review full stack trace in logs",
            "2. Check engine-specific logs",
            "3. Update dev_agent.py with new error pattern",
            "4. File issue if reproducible bug",
        ],
    }


def suggest_schema_fix(table: str, failed_fields: list) -> Dict[str, Any]:
    """
    Suggest field name corrections for schema mismatches.

    Input:
      - table: Airtable table name
      - failed_fields: list of field names that failed

    Returns suggested corrections based on common patterns.
    """
    from app_v2.llm_control.schema_map import SCHEMA

    if table not in SCHEMA:
        return {
            "status": "unknown_table",
            "message": f"Table '{table}' not in schema_map.py",
        }

    valid_fields = SCHEMA[table]
    suggestions = {}

    for failed_field in failed_fields:
        # Try to find close matches
        lower_failed = failed_field.lower().replace("_", "").replace(" ", "")

        matches = []
        for valid_field in valid_fields:
            lower_valid = valid_field.lower().replace("_", "").replace(" ", "")
            if lower_failed == lower_valid:
                matches.append(valid_field)
            elif lower_failed in lower_valid or lower_valid in lower_failed:
                matches.append(valid_field)

        suggestions[failed_field] = matches if matches else ["No close match found"]

    return {
        "status": "suggestions_generated",
        "table": table,
        "suggestions": suggestions,
        "hint": "Update engine code to use suggested field names",
    }
