#!/usr/bin/env python3
"""
Smoke tests for KRIZZY OPS v3.0.0
Tests all critical integrations and endpoints.
"""
import os
import sys
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Tuple


class SmokeTester:
    """Comprehensive smoke testing for KRIZZY OPS."""
    
    def __init__(self):
        self.base_url = f"http://localhost:{os.getenv('PORT', '8080')}"
        self.results = []
        self.start_time = time.time()
    
    def log_test(self, test_name: str, success: bool, message: str = "", duration: float = 0):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "duration": duration
        })
        print(f"{status} {test_name}: {message}")
    
    def test_health_endpoint(self) -> bool:
        """Test health endpoint returns correct format."""
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["status", "ts"]
                if all(field in data for field in required_fields):
                    if data["status"] == "ok":
                        self.log_test("Health Endpoint", True, f"Status: {data['status']}", duration)
                        return True
            
            self.log_test("Health Endpoint", False, f"Invalid response: {response.text}", duration)
            return False
            
        except Exception as e:
            duration = time.time() - start
            self.log_test("Health Endpoint", False, f"Error: {e}", duration)
            return False
    
    def test_airtable_connection(self) -> bool:
        """Test Airtable connectivity and write capability."""
        start = time.time()
        try:
            from airtable_utils import safe_airtable_write, fetch_all
            
            # Test record for smoke test
            test_record = {
                "Test_Field": f"Smoke test {datetime.now().isoformat()}",
                "Source": "smoke_test",
                "Timestamp": datetime.now().isoformat()
            }
            
            # Test write
            success, record_id = safe_airtable_write("KPI_Log", test_record, ["Test_Field"])
            duration = time.time() - start
            
            if success and record_id:
                self.log_test("Airtable Write", True, f"Record ID: {record_id}", duration)
                
                # Test fetch
                records = fetch_all("KPI_Log", max_records=1)
                if records:
                    self.log_test("Airtable Fetch", True, f"Retrieved {len(records)} records", 0)
                    return True
                else:
                    self.log_test("Airtable Fetch", False, "No records retrieved", 0)
                    return False
            else:
                self.log_test("Airtable Write", False, f"Write failed: {record_id}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start
            self.log_test("Airtable Connection", False, f"Error: {e}", duration)
            return False
    
    def test_discord_webhooks(self) -> bool:
        """Test Discord webhook connectivity."""
        start = time.time()
        try:
            from discord_utils import post_ops, post_err
            
            # Test OPS webhook
            ops_success = post_ops(f"🔍 Smoke test from KRIZZY OPS v3.0.0 at {datetime.now().isoformat()}")
            duration = time.time() - start
            
            if ops_success:
                self.log_test("Discord OPS", True, "Message sent successfully", duration)
                
                # Test ERR webhook
                err_success = post_err(f"🔍 Smoke test error from KRIZZY OPS v3.0.0 at {datetime.now().isoformat()}")
                if err_success:
                    self.log_test("Discord ERR", True, "Error message sent successfully", 0)
                    return True
                else:
                    self.log_test("Discord ERR", False, "Failed to send error message", 0)
                    return False
            else:
                self.log_test("Discord OPS", False, "Failed to send ops message", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start
            self.log_test("Discord Webhooks", False, f"Error: {e}", duration)
            return False
    
    def test_twilio_connection(self) -> bool:
        """Test Twilio connectivity."""
        start = time.time()
        try:
            from twilio_utils import twilio
            
            # Test account connectivity
            account = twilio.client.api.accounts(twilio.account_sid).fetch()
            duration = time.time() - start
            
            if account:
                self.log_test("Twilio Connection", True, f"Account: {account.friendly_name}", duration)
                return True
            else:
                self.log_test("Twilio Connection", False, "No account info retrieved", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start
            self.log_test("Twilio Connection", False, f"Error: {e}", duration)
            return False
    
    def test_sam_gov_api(self) -> bool:
        """Test SAM.gov API connectivity."""
        start = time.time()
        try:
            sam_api = os.getenv("SAM_SEARCH_API")
            if not sam_api:
                self.log_test("SAM.gov API", False, "SAM_SEARCH_API not configured", 0)
                return False
            
            # Test with minimal request
            response = requests.get(sam_api, params={"limit": 1}, timeout=15)
            duration = time.time() - start
            
            if response.status_code == 200:
                self.log_test("SAM.gov API", True, f"Status: {response.status_code}", duration)
                return True
            else:
                self.log_test("SAM.gov API", False, f"Status: {response.status_code}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start
            self.log_test("SAM.gov API", False, f"Error: {e}", duration)
            return False
    
    def test_fpds_feed(self) -> bool:
        """Test FPDS ATOM feed connectivity."""
        start = time.time()
        try:
            fpds_feed = os.getenv("FPDS_ATOM_FEED")
            if not fpds_feed:
                self.log_test("FPDS Feed", False, "FPDS_ATOM_FEED not configured", 0)
                return False
            
            response = requests.get(fpds_feed, timeout=15)
            duration = time.time() - start
            
            if response.status_code == 200:
                # Check if it's valid XML
                import xml.etree.ElementTree as ET
                try:
                    ET.fromstring(response.text)
                    self.log_test("FPDS Feed", True, f"Valid ATOM feed, Status: {response.status_code}", duration)
                    return True
                except ET.ParseError:
                    self.log_test("FPDS Feed", False, "Invalid XML response", duration)
                    return False
            else:
                self.log_test("FPDS Feed", False, f"Status: {response.status_code}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start
            self.log_test("FPDS Feed", False, f"Error: {e}", duration)
            return False
    
    def test_rei_endpoint(self) -> bool:
        """Test REI endpoint functionality."""
        start = time.time()
        try:
            response = requests.post(f"{self.base_url}/ops/rei", timeout=30)
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                if "REI_Leads" in data and "status" in data:
                    self.log_test("REI Endpoint", True, f"Leads: {data['REI_Leads']}", duration)
                    return True
                else:
                    self.log_test("REI Endpoint", False, f"Invalid response format: {data}", duration)
                    return False
            else:
                self.log_test("REI Endpoint", False, f"Status: {response.status_code}, Response: {response.text}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start
            self.log_test("REI Endpoint", False, f"Error: {e}", duration)
            return False
    
    def test_govcon_endpoint(self) -> bool:
        """Test GovCon endpoint functionality."""
        start = time.time()
        try:
            response = requests.post(f"{self.base_url}/ops/govcon", timeout=30)
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                if "GovCon_Bids" in data and "status" in data:
                    self.log_test("GovCon Endpoint", True, f"Bids: {data['GovCon_Bids']}", duration)
                    return True
                else:
                    self.log_test("GovCon Endpoint", False, f"Invalid response format: {data}", duration)
                    return False
            else:
                self.log_test("GovCon Endpoint", False, f"Status: {response.status_code}, Response: {response.text}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start
            self.log_test("GovCon Endpoint", False, f"Error: {e}", duration)
            return False
    
    def test_watchdog_endpoint(self) -> bool:
        """Test Watchdog endpoint functionality."""
        start = time.time()
        try:
            response = requests.post(f"{self.base_url}/ops/watchdog", timeout=30)
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                if "Cleaned" in data and "status" in data:
                    self.log_test("Watchdog Endpoint", True, f"Cleaned: {data['Cleaned']}", duration)
                    return True
                else:
                    self.log_test("Watchdog Endpoint", False, f"Invalid response format: {data}", duration)
                    return False
            else:
                self.log_test("Watchdog Endpoint", False, f"Status: {response.status_code}, Response: {response.text}", duration)
                return False
                
        except Exception as e:
            duration = time.time() - start
            self.log_test("Watchdog Endpoint", False, f"Error: {e}", duration)
            return False
    
    def run_all_tests(self) -> bool:
        """Run all smoke tests."""
        print("🚀 Starting KRIZZY OPS v3.0.0 Smoke Tests")
        print("=" * 50)
        
        tests = [
            self.test_health_endpoint,
            self.test_airtable_connection,
            self.test_discord_webhooks,
            self.test_twilio_connection,
            self.test_sam_gov_api,
            self.test_fpds_feed,
            self.test_rei_endpoint,
            self.test_govcon_endpoint,
            self.test_watchdog_endpoint
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                self.log_test(test.__name__, False, f"Unexpected error: {e}", 0)
        
        total_duration = time.time() - self.start_time
        
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        print(f"⏱️  Total duration: {total_duration:.2f} seconds")
        
        if passed == total:
            print("🎉 All tests passed! KRIZZY OPS is ready for production.")
            return True
        else:
            print("⚠️  Some tests failed. Please check the configuration.")
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate detailed test report."""
        total_duration = time.time() - self.start_time
        passed_tests = [r for r in self.results if r["success"]]
        failed_tests = [r for r in self.results if not r["success"]]
        
        return {
            "summary": {
                "total_tests": len(self.results),
                "passed": len(passed_tests),
                "failed": len(failed_tests),
                "success_rate": len(passed_tests) / len(self.results) * 100,
                "total_duration": total_duration
            },
            "results": self.results,
            "timestamp": datetime.now().isoformat(),
            "version": "3.0.0"
        }


def main():
    """Main smoke test runner."""
    tester = SmokeTester()
    
    # Check if server is running
    try:
        response = requests.get(f"http://localhost:{os.getenv('PORT', '8080')}/health", timeout=5)
        if response.status_code != 200:
            print("❌ KRIZZY OPS server is not running or not responding")
            print("Please start the server with: python main.py")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to KRIZZY OPS server")
        print("Please start the server with: python main.py")
        sys.exit(1)
    
    success = tester.run_all_tests()
    
    # Generate report
    report = tester.generate_report()
    with open("smoke_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: smoke_test_report.json")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()