"""Tests for rei_dispo_engine module"""

import pytest
from unittest.mock import Mock, patch
from rei_dispo_engine import (
    parse_zillow,
    parse_craigslist,
    deduplicate_leads,
    send_lead_notifications
)


class TestREIEngine:
    """Test cases for REI engine"""
    
    @patch('rei_dispo_engine.requests.get')
    def test_parse_zillow_success(self, mock_get):
        """Test successful Zillow parsing"""
        # Setup
        mock_response = Mock()
        mock_response.json.return_value = {
            "props": [
                {
                    "address": "123 Test St",
                    "city": "Test City",
                    "state": "TS",
                    "zipcode": "12345",
                    "price": 250000,
                    "brokerName": "Test Broker",
                    "brokerPhone": "+1234567890",
                    "brokerEmail": "test@example.com",
                    "detailUrl": "/test-property"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Test
        leads = parse_zillow()
        
        # Assertions
        assert len(leads) == 1
        lead = leads[0]
        assert lead["Address"] == "123 Test St"
        assert lead["City"] == "Test City"
        assert lead["State"] == "TS"
        assert lead["Zip"] == "12345"
        assert lead["Price"] == 250000
        assert lead["Agent"] == "Test Broker"
        assert lead["Phone"] == "+1234567890"
        assert lead["Email"] == "test@example.com"
        assert lead["Source"] == "Zillow"
        assert "Phone_Hash" in lead
        assert "Email_Hash" in lead
    
    @patch('rei_dispo_engine.requests.get')
    def test_parse_zillow_http_error(self, mock_get):
        """Test Zillow parsing with HTTP error"""
        # Setup
        mock_get.side_effect = Exception("Network error")
        
        # Test
        with pytest.raises(Exception):  # Should raise due to retry logic
            parse_zillow()
    
    @patch('rei_dispo_engine.requests.get')
    def test_parse_craigslist_success(self, mock_get):
        """Test successful Craigslist parsing"""
        # Setup
        mock_response = Mock()
        mock_response.text = '''<?xml version="1.0"?>
        <rss>
            <channel>
                <item>
                    <title>Test Property</title>
                    <link>https://craigslist.org/test</link>
                </item>
            </channel>
        </rss>'''
        mock_get.return_value = mock_response
        
        # Test
        leads = parse_craigslist()
        
        # Assertions
        assert len(leads) == 1
        lead = leads[0]
        assert lead["Address"] == "Test Property"
        assert lead["Source_URL"] == "https://craigslist.org/test"
        assert lead["Source"] == "Craigslist"
        assert lead["Phone"] == ""
        assert lead["Email"] == ""
    
    @patch('rei_dispo_engine.requests.get')
    def test_parse_craigslist_http_error(self, mock_get):
        """Test Craigslist parsing with HTTP error"""
        # Setup
        mock_get.side_effect = Exception("Network error")
        
        # Test
        with pytest.raises(Exception):  # Should raise due to retry logic
            parse_craigslist()
    
    def test_deduplicate_leads_no_duplicates(self):
        """Test lead deduplication with no duplicates"""
        new_leads = [
            {
                "Source_URL": "https://zillow.com/prop1",
                "Phone_Hash": "hash1",
                "Email_Hash": "email1"
            },
            {
                "Source_URL": "https://zillow.com/prop2",
                "Phone_Hash": "hash2",
                "Email_Hash": "email2"
            }
        ]
        
        existing_leads = [
            {
                "fields": {
                    "Source_URL": "https://zillow.com/prop3",
                    "Phone_Hash": "hash3",
                    "Email_Hash": "email3"
                }
            }
        ]
        
        # Test
        deduplicated = deduplicate_leads(new_leads, existing_leads)
        
        # Assertions
        assert len(deduplicated) == 2
        assert deduplicated == new_leads
    
    def test_deduplicate_leads_with_duplicates(self):
        """Test lead deduplication with duplicates"""
        new_leads = [
            {
                "Source_URL": "https://zillow.com/prop1",
                "Phone_Hash": "hash1",
                "Email_Hash": "email1"
            },
            {
                "Source_URL": "https://zillow.com/prop2",
                "Phone_Hash": "hash2",
                "Email_Hash": "email2"
            }
        ]
        
        existing_leads = [
            {
                "fields": {
                    "Source_URL": "https://zillow.com/prop1",
                    "Phone_Hash": "hash1",
                    "Email_Hash": "email1"
                }
            }
        ]
        
        # Test
        deduplicated = deduplicate_leads(new_leads, existing_leads)
        
        # Assertions
        assert len(deduplicated) == 1
        assert deduplicated[0]["Source_URL"] == "https://zillow.com/prop2"
    
    def test_deduplicate_leads_internal_duplicates(self):
        """Test lead deduplication with internal duplicates"""
        new_leads = [
            {
                "Source_URL": "https://zillow.com/prop1",
                "Phone_Hash": "hash1",
                "Email_Hash": "email1"
            },
            {
                "Source_URL": "https://zillow.com/prop1",  # Duplicate
                "Phone_Hash": "hash1",
                "Email_Hash": "email1"
            }
        ]
        
        existing_leads = []
        
        # Test
        deduplicated = deduplicate_leads(new_leads, existing_leads)
        
        # Assertions
        assert len(deduplicated) == 1
    
    @patch('rei_dispo_engine.logger')
    def test_send_lead_notifications_empty(self, mock_logger):
        """Test lead notifications with empty list"""
        # Test
        send_lead_notifications([])
        
        # Assertions - function should not log anything for empty list
        mock_logger.info.assert_not_called()
    
    @patch('rei_dispo_engine.logger')
    def test_send_lead_notifications_with_leads(self, mock_logger):
        """Test lead notifications with leads"""
        leads = [
            {
                "Address": "123 Test St",
                "Price": 250000,
                "Phone": "+1234567890"
            }
        ]
        
        # Test
        send_lead_notifications(leads)
        
        # Assertions
        mock_logger.info.assert_called_with("Would send notifications for 1 new leads")
    
    @patch('rei_dispo_engine.parse_zillow')
    @patch('rei_dispo_engine.parse_craigslist')
    @patch('rei_dispo_engine.fetch_all')
    @patch('rei_dispo_engine.deduplicate_leads')
    @patch('rei_dispo_engine.safe_airtable_write')
    @patch('rei_dispo_engine.send_lead_notifications')
    @patch('rei_dispo_engine.track_cycle_start')
    @patch('rei_dispo_engine.track_cycle_end')
    def test_run_rei_success(self, mock_track_end, mock_track_start, mock_notifications,
                            mock_write, mock_dedupe, mock_fetch, mock_craigslist, mock_zillow):
        """Test successful REI engine run"""
        # Setup
        mock_zillow.return_value = [{"Address": "123 Test St", "Phone": "+1234567890"}]
        mock_craigslist.return_value = [{"Address": "456 Test Ave", "Email": "test@example.com"}]
        mock_fetch.return_value = []
        mock_dedupe.return_value = [{"Address": "123 Test St", "Phone": "+1234567890"}]
        mock_write.return_value = {"id": "test_id"}
        
        # Test
        from rei_dispo_engine import run_rei
        result = run_rei()
        
        # Assertions
        assert result == 1
        mock_track_start.assert_called_once_with("REI")
        mock_track_end.assert_called_once_with("REI", 1, success=True)
        mock_write.assert_called_once()
        mock_notifications.assert_called_once()
    
    @patch('rei_dispo_engine.parse_zillow')
    @patch('rei_dispo_engine.track_cycle_start')
    @patch('rei_dispo_engine.track_error')
    def test_run_rei_failure(self, mock_track_error, mock_track_start, mock_zillow):
        """Test REI engine run with failure"""
        # Setup
        mock_zillow.side_effect = Exception("API Error")
        
        # Test
        from rei_dispo_engine import run_rei
        result = run_rei()
        
        # Assertions
        assert result == 0
        mock_track_start.assert_called_once_with("REI")
        mock_track_error.assert_called_once()