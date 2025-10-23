"""Tests for govcon_subtrap_engine module"""

import pytest
from unittest.mock import Mock, patch
from govcon_subtrap_engine import (
    is_naics_whitelisted, 
    is_due_within_days, 
    is_combined_synopsis_solicitation,
    filter_opportunities,
    build_bid_pack_json
)


class TestGovConEngine:
    """Test cases for GovCon engine"""
    
    def test_is_naics_whitelisted_with_whitelist(self):
        """Test NAICS whitelist filtering with whitelist configured"""
        with patch('govcon_subtrap_engine.NAICS_WHITELIST', ['541511', '541512']):
            assert is_naics_whitelisted('541511') is True
            assert is_naics_whitelisted('541512') is True
            assert is_naics_whitelisted('541513') is False
            assert is_naics_whitelisted('') is True  # Empty string should be allowed
    
    def test_is_naics_whitelisted_no_whitelist(self):
        """Test NAICS whitelist filtering with no whitelist"""
        with patch('govcon_subtrap_engine.NAICS_WHITELIST', []):
            assert is_naics_whitelisted('541511') is True
            assert is_naics_whitelisted('') is True
    
    def test_is_due_within_days_valid_dates(self):
        """Test due date filtering with valid dates"""
        import datetime
        
        # Test within 7 days
        future_date = (datetime.date.today() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
        assert is_due_within_days(future_date, 7) is True
        
        # Test beyond 7 days
        future_date = (datetime.date.today() + datetime.timedelta(days=10)).strftime("%Y-%m-%d")
        assert is_due_within_days(future_date, 7) is False
        
        # Test past date
        past_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        assert is_due_within_days(past_date, 7) is True
    
    def test_is_due_within_days_invalid_dates(self):
        """Test due date filtering with invalid dates"""
        assert is_due_within_days("", 7) is False
        assert is_due_within_days("invalid-date", 7) is False
        assert is_due_within_days(None, 7) is False
    
    def test_is_combined_synopsis_solicitation_valid(self):
        """Test combined synopsis/solicitation detection"""
        # Test with opportunity type
        assert is_combined_synopsis_solicitation("Combined Synopsis/Solicitation", "") is True
        assert is_combined_synopsis_solicitation("RFP", "") is True
        assert is_combined_synopsis_solicitation("RFI", "") is True
        assert is_combined_synopsis_solicitation("RFQ", "") is True
        
        # Test with title
        assert is_combined_synopsis_solicitation("", "Combined Synopsis for IT Services") is True
        assert is_combined_synopsis_solicitation("", "RFP - Software") is True
        
        # Test with both
        assert is_combined_synopsis_solicitation("Solicitation", "Combined RFP") is True
    
    def test_is_combined_synopsis_solicitation_invalid(self):
        """Test combined synopsis/solicitation detection with invalid inputs"""
        assert is_combined_synopsis_solicitation("", "") is False
        assert is_combined_synopsis_solicitation("Award", "Contract Award") is False
        assert is_combined_synopsis_solicitation("Modification", "Contract Modification") is False
    
    def test_filter_opportunities(self):
        """Test opportunity filtering logic"""
        opportunities = [
            {
                "solicitationNumber": "12345",
                "naicsCode": "541511",
                "responseDate": "2024-01-15",
                "type": "Combined Synopsis/Solicitation",
                "title": "IT Services RFP",
                "officers": [{"email": "test@example.com", "fullName": "John Doe"}]
            },
            {
                "solicitationNumber": "12346",
                "naicsCode": "541999",  # Not in whitelist
                "responseDate": "2024-01-15",
                "type": "Combined Synopsis/Solicitation",
                "title": "Other Services",
                "officers": [{"email": "test2@example.com", "fullName": "Jane Doe"}]
            },
            {
                "solicitationNumber": "12347",
                "naicsCode": "541511",
                "responseDate": "2024-12-31",  # Too far out
                "type": "Combined Synopsis/Solicitation",
                "title": "Future Services",
                "officers": [{"email": "test3@example.com", "fullName": "Bob Smith"}]
            },
            {
                "solicitationNumber": "12348",
                "naicsCode": "541511",
                "responseDate": "2024-01-15",
                "type": "Award",  # Not combined synopsis
                "title": "Contract Award",
                "officers": [{"email": "test4@example.com", "fullName": "Alice Johnson"}]
            }
        ]
        
        with patch('govcon_subtrap_engine.NAICS_WHITELIST', ['541511']):
            filtered = filter_opportunities(opportunities)
            
            # Should return opportunities 1 and 3 (both have valid NAICS and due dates)
            assert len(filtered) == 2
            assert filtered[0]["solicitationNumber"] == "12345"
            assert filtered[1]["solicitationNumber"] == "12347"
    
    def test_build_bid_pack_json(self):
        """Test bid pack JSON generation"""
        opportunity = {
            "solicitationNumber": "12345",
            "title": "IT Services RFP",
            "naicsCode": "541511",
            "responseDate": "2024-01-15",
            "officers": [{"email": "test@example.com", "fullName": "John Doe"}],
            "type": "Combined Synopsis/Solicitation",
            "uiLink": "https://sam.gov/12345",
            "description": "IT services procurement",
            "estimatedValue": "100000"
        }
        
        with patch('govcon_subtrap_engine.UEI', 'TEST123456789'), \
             patch('govcon_subtrap_engine.CAGE_CODE', 'ABC12'):
            
            bid_pack = build_bid_pack_json(opportunity)
            
            assert bid_pack["solicitation_number"] == "12345"
            assert bid_pack["title"] == "IT Services RFP"
            assert bid_pack["naics_code"] == "541511"
            assert bid_pack["due_date"] == "2024-01-15"
            assert bid_pack["officer_name"] == "John Doe"
            assert bid_pack["officer_email"] == "test@example.com"
            assert bid_pack["opportunity_type"] == "Combined Synopsis/Solicitation"
            assert bid_pack["ui_link"] == "https://sam.gov/12345"
            assert bid_pack["description"] == "IT services procurement"
            assert bid_pack["estimated_value"] == "100000"
            assert bid_pack["uei"] == "TEST123456789"
            assert bid_pack["cage_code"] == "ABC12"
            assert "timestamp" in bid_pack
    
    @patch('govcon_subtrap_engine.fetch_sam_opportunities')
    @patch('govcon_subtrap_engine.fetch_fpds_data')
    @patch('govcon_subtrap_engine.filter_opportunities')
    @patch('govcon_subtrap_engine.safe_airtable_write')
    @patch('govcon_subtrap_engine.track_cycle_start')
    @patch('govcon_subtrap_engine.track_cycle_end')
    def test_run_govcon_success(self, mock_track_end, mock_track_start, mock_write, 
                               mock_filter, mock_fpds, mock_sam):
        """Test successful GovCon engine run"""
        # Setup
        mock_sam.return_value = [{"solicitationNumber": "12345", "naicsCode": "541511"}]
        mock_fpds.return_value = [{"title": "Test Award"}]
        mock_filter.return_value = [{"solicitationNumber": "12345", "naicsCode": "541511"}]
        mock_write.return_value = {"id": "test_id"}
        
        # Test
        from govcon_subtrap_engine import run_govcon
        result = run_govcon()
        
        # Assertions
        assert result == 1
        mock_track_start.assert_called_once_with("GovCon")
        mock_track_end.assert_called_once_with("GovCon", 1, True)
        mock_write.assert_called_once()
    
    @patch('govcon_subtrap_engine.fetch_sam_opportunities')
    @patch('govcon_subtrap_engine.track_cycle_start')
    @patch('govcon_subtrap_engine.track_error')
    def test_run_govcon_failure(self, mock_track_error, mock_track_start, mock_sam):
        """Test GovCon engine run with failure"""
        # Setup
        mock_sam.side_effect = Exception("API Error")
        
        # Test
        from govcon_subtrap_engine import run_govcon
        result = run_govcon()
        
        # Assertions
        assert result == 0
        mock_track_start.assert_called_once_with("GovCon")
        mock_track_error.assert_called_once()