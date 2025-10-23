#!/usr/bin/env python3
"""Smoke tests for KRIZZY OPS production readiness."""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()


def color_print(message: str, success: bool) -> None:
    """Print colored message."""
    symbol = "✅" if success else "❌"
    print(f"{symbol} {message}")


def test_airtable() -> bool:
    """Test Airtable connection and operations."""
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not api_key or not base_id:
        color_print("Airtable: Missing credentials (AIRTABLE_API_KEY or AIRTABLE_BASE_ID)", False)
        return False

    try:
        from pyairtable import Table

        table = Table(api_key, base_id, "KPI_Log")

        test_record = {
            "Event": "smoke_test",
            "Data": "test",
            "Timestamp": "2025-10-23T00:00:00Z"
        }
        created = table.create(test_record)
        record_id = created["id"]

        updated = table.update(record_id, {"Event": "smoke_test_updated"})

        table.delete(record_id)

        color_print("Airtable: create+upsert test record ➜ 200 OK", True)
        return True

    except Exception as e:
        color_print(f"Airtable: FAILED - {e}", False)
        return False


def test_discord() -> bool:
    """Test Discord webhooks."""
    ops_webhook = os.getenv("DISCORD_WEBHOOK_OPS")
    err_webhook = os.getenv("DISCORD_WEBHOOK_ERRORS")

    if not ops_webhook or not err_webhook:
        color_print("Discord: Missing webhooks (DISCORD_WEBHOOK_OPS or DISCORD_WEBHOOK_ERRORS)", False)
        return False

    success = True

    try:
        response = requests.post(
            ops_webhook,
            json={"content": "✅ Smoke test: ops channel"},
            timeout=10
        )
        if response.status_code in (200, 204):
            color_print("Discord: post to #ops ➜ 204/200 OK", True)
        else:
            color_print(f"Discord: post to #ops ➜ {response.status_code}", False)
            success = False
    except Exception as e:
        color_print(f"Discord: post to #ops FAILED - {e}", False)
        success = False

    try:
        response = requests.post(
            err_webhook,
            json={"content": "❌ Smoke test: errors channel"},
            timeout=10
        )
        if response.status_code in (200, 204):
            color_print("Discord: post to #errors ➜ 204/200 OK", True)
        else:
            color_print(f"Discord: post to #errors ➜ {response.status_code}", False)
            success = False
    except Exception as e:
        color_print(f"Discord: post to #errors FAILED - {e}", False)
        success = False

    return success


def test_twilio() -> bool:
    """Test Twilio connection."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        color_print("Twilio: Missing credentials (TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN)", False)
        return False

    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        account = client.api.accounts(account_sid).fetch()

        if account.status == "active":
            color_print("Twilio: fetch account SID ➜ 200 OK", True)
            return True
        else:
            color_print(f"Twilio: account status is {account.status}", False)
            return False

    except Exception as e:
        color_print(f"Twilio: FAILED - {e}", False)
        return False


def test_sam_fpds() -> bool:
    """Test SAM.gov and FPDS endpoints."""
    sam_api = os.getenv("SAM_SEARCH_API")
    fpds_feed = os.getenv("FPDS_ATOM_FEED")

    success = True

    if sam_api:
        try:
            response = requests.get(sam_api, params={"limit": 1}, timeout=30)
            if response.status_code == 200:
                color_print("SAM.gov: GET endpoint ➜ 200 OK", True)
            else:
                color_print(f"SAM.gov: GET endpoint ➜ {response.status_code}", False)
                success = False
        except Exception as e:
            color_print(f"SAM.gov: FAILED - {e}", False)
            success = False
    else:
        color_print("SAM.gov: SAM_SEARCH_API not configured", False)
        success = False

    if fpds_feed:
        try:
            response = requests.get(fpds_feed, timeout=30)
            if response.status_code == 200:
                color_print("FPDS: GET endpoint ➜ 200 OK", True)
            else:
                color_print(f"FPDS: GET endpoint ➜ {response.status_code}", False)
                success = False
        except Exception as e:
            color_print(f"FPDS: FAILED - {e}", False)
            success = False
    else:
        color_print("FPDS: FPDS_ATOM_FEED not configured (optional)", True)

    return success


def test_health_endpoint() -> bool:
    """Test local health endpoint."""
    port = os.getenv("PORT", "8080")

    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        data = response.json()

        if response.status_code == 200 and data.get("status") == "ok" and "ts" in data:
            color_print(f"Health: GET /health ➜ status ok with timestamp", True)
            return True
        else:
            color_print(f"Health: GET /health ➜ unexpected response", False)
            return False

    except requests.exceptions.ConnectionError:
        color_print("Health: Server not running (start with 'python main.py')", False)
        return False
    except Exception as e:
        color_print(f"Health: FAILED - {e}", False)
        return False


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("KRIZZY OPS SMOKE TESTS")
    print("=" * 60)
    print()

    results = {
        "Airtable": test_airtable(),
        "Discord": test_discord(),
        "Twilio": test_twilio(),
        "SAM/FPDS": test_sam_fpds(),
        "Health": test_health_endpoint(),
    }

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for name, success in results.items():
        status = "PASS" if success else "FAIL"
        color_print(f"{name}: {status}", success)

    print()
    print(f"Passed: {passed}/{total}")
    print()

    if passed == total:
        print("✅ ALL SMOKE TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ SOME SMOKE TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
