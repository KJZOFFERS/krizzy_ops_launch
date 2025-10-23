#!/usr/bin/env python3
"""
KRIZZY OPS Smoke Test Suite

Comprehensive acceptance tests to verify all systems are operational.
Must pass before production deployment.

Usage: python tools/smoke.py
"""

import logging
import os
import sys
import time
from datetime import datetime

import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyairtable import Table
from twilio.rest import Client

from airtable_utils import fetch_all, kpi_push, safe_airtable_write
from discord_utils import post_error, post_ops
from twilio_utils import format_phone_number

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
TEST_TIMEOUT = 30
REQUIRED_ENV_VARS = [
    'AIRTABLE_API_KEY',
    'AIRTABLE_BASE_ID',
    'DISCORD_WEBHOOK_OPS',
    'DISCORD_WEBHOOK_ERRORS',
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
    'TWILIO_MESSAGING_SERVICE_SID',
]

# Test results tracking
test_results: list[tuple[str, bool, str]] = []


def log_test_result(test_name: str, success: bool, message: str = ""):
    """Log and track test results."""
    status = "✅ PASS" if success else "❌ FAIL"
    logger.info(f"{status}: {test_name} - {message}")
    test_results.append((test_name, success, message))


def check_environment_variables() -> bool:
    """Check that all required environment variables are set."""
    logger.info("🔍 Checking environment variables...")

    missing_vars = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        log_test_result("Environment Variables", False, f"Missing: {', '.join(missing_vars)}")
        return False

    log_test_result("Environment Variables", True, "All required vars present")
    return True


def test_airtable_connection() -> bool:
    """Test Airtable API connection and operations."""
    logger.info("🗃️  Testing Airtable connection...")

    try:
        # Test basic connection
        table = Table(os.getenv('AIRTABLE_API_KEY'), os.getenv('AIRTABLE_BASE_ID'), 'KPI_Log')

        # Test fetch operation
        records = table.all(max_records=1)
        log_test_result("Airtable Fetch", True, f"Retrieved {len(records)} records")

        # Test create operation with test record
        test_record = {
            "Event": "smoke_test",
            "Timestamp": datetime.utcnow().isoformat(),
            "Data": "Smoke test record",
            "Count": 1,
            "Status": "test",
        }

        created = safe_airtable_write("KPI_Log", test_record, ["Event", "Timestamp"])
        if created:
            log_test_result("Airtable Create", True, f"Created record: {created['id']}")

            # Test upsert (update existing)
            test_record["Data"] = "Updated smoke test record"
            updated = safe_airtable_write("KPI_Log", test_record, ["Event", "Timestamp"])
            if updated:
                log_test_result("Airtable Upsert", True, f"Updated record: {updated['id']}")
                return True
            else:
                log_test_result("Airtable Upsert", False, "Failed to update record")
                return False
        else:
            log_test_result("Airtable Create", False, "Failed to create record")
            return False

    except Exception as e:
        log_test_result("Airtable Connection", False, str(e))
        return False


def test_discord_webhooks() -> bool:
    """Test Discord webhook functionality."""
    logger.info("💬 Testing Discord webhooks...")

    success = True

    # Test ops webhook
    try:
        ops_result = post_ops("Smoke test - OPS channel verification")
        if ops_result:
            log_test_result("Discord OPS Webhook", True, "Message sent successfully")
        else:
            log_test_result("Discord OPS Webhook", False, "Failed to send message")
            success = False
    except Exception as e:
        log_test_result("Discord OPS Webhook", False, str(e))
        success = False

    # Test errors webhook
    try:
        error_result = post_error("Smoke test - ERRORS channel verification")
        if error_result:
            log_test_result("Discord ERRORS Webhook", True, "Message sent successfully")
        else:
            log_test_result("Discord ERRORS Webhook", False, "Failed to send message")
            success = False
    except Exception as e:
        log_test_result("Discord ERRORS Webhook", False, str(e))
        success = False

    return success


def test_twilio_connection() -> bool:
    """Test Twilio API connection."""
    logger.info("📱 Testing Twilio connection...")

    try:
        # Test basic connection by fetching account info
        client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))

        account = client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch()
        log_test_result("Twilio Account Fetch", True, f"Account SID: {account.sid[:8]}...")

        # Test messaging service
        messaging_service_sid = os.getenv('TWILIO_MESSAGING_SERVICE_SID')
        if messaging_service_sid:
            try:
                service = client.messaging.services(messaging_service_sid).fetch()
                log_test_result(
                    "Twilio Messaging Service", True, f"Service: {service.friendly_name}"
                )
            except Exception as e:
                log_test_result("Twilio Messaging Service", False, str(e))
                return False

        # Test phone number formatting
        test_phone = "5551234567"
        formatted = format_phone_number(test_phone)
        if formatted == "+15551234567":
            log_test_result("Phone Formatting", True, f"{test_phone} -> {formatted}")
        else:
            log_test_result("Phone Formatting", False, f"Expected +15551234567, got {formatted}")
            return False

        return True

    except Exception as e:
        log_test_result("Twilio Connection", False, str(e))
        return False


def test_sam_gov_api() -> bool:
    """Test SAM.gov API endpoint accessibility."""
    logger.info("🏛️  Testing SAM.gov API...")

    try:
        sam_api_url = os.getenv('SAM_SEARCH_API', 'https://api.sam.gov/opportunities/v2/search')

        # Test basic connectivity
        response = requests.get(
            sam_api_url,
            params={'limit': 1},
            timeout=TEST_TIMEOUT,
            headers={'User-Agent': 'KRIZZY-OPS-SmokeTest/1.0'},
        )

        if response.status_code == 200:
            data = response.json()
            opportunities = data.get('opportunitiesData', [])
            log_test_result(
                "SAM.gov API",
                True,
                f"Status: {response.status_code}, Opportunities: {len(opportunities)}",
            )
            return True
        else:
            log_test_result(
                "SAM.gov API", False, f"HTTP {response.status_code}: {response.text[:100]}"
            )
            return False

    except Exception as e:
        log_test_result("SAM.gov API", False, str(e))
        return False


def test_fpds_feed() -> bool:
    """Test FPDS ATOM feed accessibility."""
    logger.info("📋 Testing FPDS feed...")

    try:
        fpds_url = os.getenv(
            'FPDS_ATOM_FEED',
            'https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=ACTIVE_DATE:[NOW-7DAYS+TO+NOW]',
        )

        response = requests.get(
            fpds_url, timeout=TEST_TIMEOUT, headers={'User-Agent': 'KRIZZY-OPS-SmokeTest/1.0'}
        )

        if response.status_code == 200:
            # Basic XML validation
            if '<feed' in response.text and '</feed>' in response.text:
                log_test_result("FPDS Feed", True, f"Status: {response.status_code}, Valid XML")
                return True
            else:
                log_test_result("FPDS Feed", False, "Invalid XML format")
                return False
        else:
            log_test_result(
                "FPDS Feed", False, f"HTTP {response.status_code}: {response.text[:100]}"
            )
            return False

    except Exception as e:
        log_test_result("FPDS Feed", False, str(e))
        return False


def test_health_endpoint() -> bool:
    """Test application health endpoint."""
    logger.info("🏥 Testing health endpoint...")

    try:
        port = os.getenv('PORT', '8080')
        health_url = f"http://localhost:{port}/health"

        response = requests.get(health_url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ok' and 'ts' in data:
                log_test_result("Health Endpoint", True, f"Status: {data['status']}")
                return True
            else:
                log_test_result("Health Endpoint", False, f"Invalid response: {data}")
                return False
        else:
            log_test_result("Health Endpoint", False, f"HTTP {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        log_test_result("Health Endpoint", False, "Service not running")
        return False
    except Exception as e:
        log_test_result("Health Endpoint", False, str(e))
        return False


def test_kpi_system() -> bool:
    """Test KPI logging system."""
    logger.info("📊 Testing KPI system...")

    try:
        # Test KPI push
        test_data = {"test_metric": "smoke_test", "count": 42, "status": "testing"}

        kpi_push("smoke_test_kpi", test_data)

        # Verify KPI was logged
        time.sleep(2)  # Allow time for async operations

        kpi_records = fetch_all("KPI_Log")
        smoke_test_kpis = [
            r for r in kpi_records if r.get("fields", {}).get("Event") == "smoke_test_kpi"
        ]

        if smoke_test_kpis:
            log_test_result("KPI System", True, f"Found {len(smoke_test_kpis)} KPI records")
            return True
        else:
            log_test_result("KPI System", False, "KPI record not found")
            return False

    except Exception as e:
        log_test_result("KPI System", False, str(e))
        return False


def run_comprehensive_smoke_test() -> bool:
    """Run all smoke tests and return overall success."""
    logger.info("🚀 Starting KRIZZY OPS Smoke Test Suite")
    logger.info("=" * 60)

    start_time = datetime.utcnow()

    # Run all tests
    tests = [
        ("Environment Check", check_environment_variables),
        ("Airtable Connection", test_airtable_connection),
        ("Discord Webhooks", test_discord_webhooks),
        ("Twilio Connection", test_twilio_connection),
        ("SAM.gov API", test_sam_gov_api),
        ("FPDS Feed", test_fpds_feed),
        ("KPI System", test_kpi_system),
        ("Health Endpoint", test_health_endpoint),
    ]

    all_passed = True

    for test_name, test_func in tests:
        try:
            success = test_func()
            if not success:
                all_passed = False
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            log_test_result(test_name, False, f"Test crashed: {str(e)}")
            all_passed = False

        time.sleep(1)  # Brief pause between tests

    # Generate summary report
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    logger.info("=" * 60)
    logger.info("📋 SMOKE TEST SUMMARY")
    logger.info("=" * 60)

    passed_count = sum(1 for _, success, _ in test_results if success)
    total_count = len(test_results)

    logger.info(f"Duration: {duration:.1f} seconds")
    logger.info(f"Tests Passed: {passed_count}/{total_count}")

    if all_passed:
        logger.info("🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")

        # Log success to Discord
        try:
            post_ops(
                f"🎉 KRIZZY OPS Smoke Test PASSED - {passed_count}/{total_count} tests successful in {duration:.1f}s"
            )
        except:
            pass  # Don't fail if Discord notification fails

    else:
        logger.error("❌ SOME TESTS FAILED - SYSTEM NOT READY")

        # Log failures
        failed_tests = [name for name, success, _ in test_results if not success]
        logger.error(f"Failed tests: {', '.join(failed_tests)}")

        try:
            post_error(
                f"❌ KRIZZY OPS Smoke Test FAILED - {len(failed_tests)} tests failed: {', '.join(failed_tests)}"
            )
        except:
            pass

    logger.info("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = run_comprehensive_smoke_test()
    sys.exit(0 if success else 1)
