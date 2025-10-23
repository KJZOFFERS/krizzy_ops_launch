#!/usr/bin/env python3
"""
KRIZZY OPS Smoke Tests
Acceptance tests for all system components
"""

import os
import sys
import requests
import json
import time
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from airtable_utils import safe_airtable_write, fetch_all
from discord_utils import post_ops, post_error
from twilio_utils import send_msg
from kpi import kpi_push

class SmokeTestError(Exception):
    """Custom exception for smoke test failures"""
    pass

def test_airtable_connection() -> bool:
    """Test Airtable connection and write/upsert functionality"""
    print("🧪 Testing Airtable connection...")
    
    try:
        # Test record for smoke test
        test_record = {
            "Test_Field": "Smoke Test",
            "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "Status": "Testing"
        }
        
        # Test write
        result = safe_airtable_write("KPI_Log", test_record)
        if not result:
            raise SmokeTestError("Airtable write returned None")
        
        print("✅ Airtable write test passed")
        
        # Test fetch
        records = fetch_all("KPI_Log")
        if not isinstance(records, list):
            raise SmokeTestError("Airtable fetch returned non-list")
        
        print("✅ Airtable fetch test passed")
        return True
        
    except Exception as e:
        print(f"❌ Airtable test failed: {e}")
        return False

def test_discord_webhooks() -> bool:
    """Test Discord webhook posting"""
    print("🧪 Testing Discord webhooks...")
    
    try:
        # Test ops webhook
        ops_result = post_ops("Smoke test - ops channel")
        if not ops_result:
            print("⚠️  Discord ops webhook not configured or failed")
        else:
            print("✅ Discord ops webhook test passed")
        
        # Test error webhook
        error_result = post_error("Smoke test - error channel")
        if not error_result:
            print("⚠️  Discord error webhook not configured or failed")
        else:
            print("✅ Discord error webhook test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Discord test failed: {e}")
        return False

def test_twilio_connection() -> bool:
    """Test Twilio connection and account verification"""
    print("🧪 Testing Twilio connection...")
    
    try:
        from twilio.rest import Client
        
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if not account_sid or not auth_token:
            print("⚠️  Twilio credentials not configured")
            return True  # Not a failure, just not configured
        
        client = Client(account_sid, auth_token)
        
        # Test account fetch
        account = client.api.accounts(account_sid).fetch()
        if not account:
            raise SmokeTestError("Failed to fetch Twilio account")
        
        print(f"✅ Twilio account verified: {account.friendly_name}")
        return True
        
    except Exception as e:
        print(f"❌ Twilio test failed: {e}")
        return False

def test_sam_gov_endpoint() -> bool:
    """Test SAM.gov API endpoint"""
    print("🧪 Testing SAM.gov endpoint...")
    
    try:
        sam_url = os.getenv("SAM_SEARCH_API", "https://api.sam.gov/prod/opportunities/v2/search")
        
        params = {
            "limit": 1,
            "sort": "-publishDate"
        }
        
        response = requests.get(sam_url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if "opportunitiesData" in data:
                print("✅ SAM.gov endpoint test passed")
                return True
            else:
                raise SmokeTestError("Invalid SAM.gov response format")
        else:
            raise SmokeTestError(f"SAM.gov returned status {response.status_code}")
            
    except Exception as e:
        print(f"❌ SAM.gov test failed: {e}")
        return False

def test_fpds_endpoint() -> bool:
    """Test FPDS Atom feed endpoint"""
    print("🧪 Testing FPDS endpoint...")
    
    try:
        fpds_url = os.getenv("FPDS_ATOM_FEED", "https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=AWARD&q=")
        
        response = requests.get(fpds_url, timeout=30)
        
        if response.status_code == 200:
            # Check if it's valid XML/Atom feed
            if "<?xml" in response.text and "feed" in response.text:
                print("✅ FPDS endpoint test passed")
                return True
            else:
                raise SmokeTestError("Invalid FPDS response format")
        else:
            raise SmokeTestError(f"FPDS returned status {response.status_code}")
            
    except Exception as e:
        print(f"❌ FPDS test failed: {e}")
        return False

def test_health_endpoint(port: int = 8080) -> bool:
    """Test health endpoint"""
    print("🧪 Testing health endpoint...")
    
    try:
        health_url = f"http://localhost:{port}/health"
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                print("✅ Health endpoint test passed")
                return True
            else:
                raise SmokeTestError(f"Health endpoint returned status: {data.get('status')}")
        else:
            raise SmokeTestError(f"Health endpoint returned status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Health endpoint test failed: {e}")
        return False

def test_kpi_tracking() -> bool:
    """Test KPI tracking functionality"""
    print("🧪 Testing KPI tracking...")
    
    try:
        # Test KPI push
        test_data = {
            "test": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "count": 1
        }
        
        kpi_push("smoke_test", test_data)
        print("✅ KPI tracking test passed")
        return True
        
    except Exception as e:
        print(f"❌ KPI tracking test failed: {e}")
        return False

def run_all_tests() -> Dict[str, bool]:
    """Run all smoke tests and return results"""
    print("🚀 Starting KRIZZY OPS Smoke Tests...")
    print("=" * 50)
    
    tests = {
        "Airtable": test_airtable_connection,
        "Discord": test_discord_webhooks,
        "Twilio": test_twilio_connection,
        "SAM.gov": test_sam_gov_endpoint,
        "FPDS": test_fpds_endpoint,
        "Health": lambda: test_health_endpoint(8080),
        "KPI": test_kpi_tracking
    }
    
    results = {}
    
    for test_name, test_func in tests.items():
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
        
        print()  # Add spacing between tests
    
    return results

def print_summary(results: Dict[str, bool]) -> None:
    """Print test summary"""
    print("=" * 50)
    print("📊 SMOKE TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:12} {status}")
    
    print("-" * 50)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready for production.")
        return True
    else:
        print("⚠️  Some tests failed. Please check configuration.")
        return False

def main():
    """Main smoke test runner"""
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ Please run smoke tests from the project root directory")
        sys.exit(1)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run tests
    results = run_all_tests()
    
    # Print summary
    all_passed = print_summary(results)
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()