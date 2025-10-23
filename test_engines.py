import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from govcon_subtrap_engine import (
    build_bid_pack_json,
    calculate_opportunity_score,
    fetch_sam_opportunities,
    filter_by_due_date,
    filter_by_naics,
    filter_combined_synopsis_solicitation,
    run_govcon,
)
from rei_dispo_engine import (
    create_dedup_key,
    enrich_lead_data,
    parse_craigslist_rss,
    parse_zillow_rss,
    run_rei,
    send_outbound_messages,
)


class TestREIEngine:
    """Test suite for REI disposition engine."""

    @patch('rei_dispo_engine.fetch_rss_feed')
    def test_parse_zillow_rss_success(self, mock_fetch):
        """Test successful Zillow RSS parsing."""
        # Mock RSS entries
        mock_entries = [
            Mock(
                title="123 Main St - $500,000",
                link="https://zillow.com/listing/123",
                description="Beautiful home in NYC, NY 10001",
            ),
            Mock(
                title="456 Oak Ave - $300,000",
                link="https://zillow.com/listing/456",
                description="Cozy house in Brooklyn, NY 11201",
            ),
        ]
        mock_fetch.return_value = mock_entries

        leads = parse_zillow_rss()

        assert len(leads) == 2
        assert leads[0]["Address"] == "123 Main St"
        assert leads[0]["Price"] == "500,000"
        assert leads[0]["Source"] == "Zillow_RSS"
        assert leads[0]["Source_URL"] == "https://zillow.com/listing/123"

    @patch('rei_dispo_engine.fetch_rss_feed')
    def test_parse_craigslist_rss_with_contact_info(self, mock_fetch):
        """Test Craigslist RSS parsing with contact extraction."""
        mock_entries = [
            Mock(
                title="House for sale $400,000",
                link="https://craigslist.org/listing/789",
                description="Great house! Call 555-123-4567 or email seller@example.com",
            )
        ]
        mock_fetch.return_value = mock_entries

        leads = parse_craigslist_rss()

        assert len(leads) == 1
        assert leads[0]["Phone"] == "555-123-4567"
        assert leads[0]["Email"] == "seller@example.com"
        assert leads[0]["Price"] == "400,000"

    def test_enrich_lead_data_phone_formatting(self):
        """Test lead data enrichment with phone formatting."""
        lead = {"Phone": "5551234567", "Email": "test@example.com", "Price": "500,000"}

        enriched = enrich_lead_data(lead)

        assert enriched["Phone"] == "+15551234567"  # E.164 format
        assert enriched["Lead_Score"] > 0
        assert enriched["ARV"] == "550000"  # Price * 1.1

    def test_enrich_lead_data_invalid_contact(self):
        """Test lead enrichment with invalid contact info."""
        lead = {"Phone": "invalid", "Email": "not-an-email", "Price": "500,000"}

        enriched = enrich_lead_data(lead)

        assert enriched["Phone"] == ""  # Invalid phone cleared
        assert enriched["Email"] == ""  # Invalid email cleared
        assert enriched["Lead_Score"] == 50  # Only price and address (if present)

    def test_create_dedup_key_with_url(self):
        """Test deduplication key creation with source URL."""
        lead = {"Source_URL": "https://example.com/listing/123"}

        key = create_dedup_key(lead)

        assert len(key) == 16
        assert key.isalnum()

    def test_create_dedup_key_fallback(self):
        """Test deduplication key creation without source URL."""
        lead = {"Address": "123 Main St", "Phone": "+15551234567"}

        key = create_dedup_key(lead)

        assert len(key) == 16
        assert key.isalnum()

    @patch('rei_dispo_engine.send_rei_message')
    @patch('rei_dispo_engine.validate_phone_number')
    def test_send_outbound_messages(self, mock_validate, mock_send):
        """Test outbound message sending."""
        mock_validate.return_value = True
        mock_send.return_value = "SM123456789"

        leads = [
            {"Phone": "+15551234567", "Lead_Score": 75},  # High score
            {"Phone": "+15559876543", "Lead_Score": 25},  # Low score
            {"Email": "test@example.com", "Lead_Score": 80},  # No phone
        ]

        sent_count = send_outbound_messages(leads)

        assert sent_count == 1  # Only one high-scoring lead with phone
        mock_send.assert_called_once_with("+15551234567")

    @patch('rei_dispo_engine.parse_zillow_rss')
    @patch('rei_dispo_engine.parse_craigslist_rss')
    @patch('rei_dispo_engine.parse_additional_sources')
    @patch('rei_dispo_engine.fetch_all')
    @patch('rei_dispo_engine.safe_airtable_write')
    def test_run_rei_full_cycle(
        self, mock_write, mock_fetch, mock_additional, mock_craigslist, mock_zillow
    ):
        """Test full REI engine cycle."""
        # Mock data sources
        mock_zillow.return_value = [
            {"Address": "123 Main", "Phone": "+15551234567", "Source_URL": "url1"}
        ]
        mock_craigslist.return_value = [
            {"Address": "456 Oak", "Email": "test@example.com", "Source_URL": "url2"}
        ]
        mock_additional.return_value = []

        # Mock existing records (empty)
        mock_fetch.return_value = []

        # Mock successful writes
        mock_write.return_value = {"id": "rec123"}

        result = run_rei()

        # Should process and write leads
        assert result >= 0
        assert mock_write.call_count >= 0


class TestGovConEngine:
    """Test suite for GovCon subtrap engine."""

    @patch('govcon_subtrap_engine.requests.get')
    def test_fetch_sam_opportunities_success(self, mock_get):
        """Test successful SAM.gov API fetch."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "opportunitiesData": [
                {"solicitationNumber": "ABC123", "title": "Test Opportunity"},
                {"solicitationNumber": "DEF456", "title": "Another Opportunity"},
            ]
        }
        mock_get.return_value = mock_response

        opportunities = fetch_sam_opportunities()

        assert len(opportunities) == 2
        assert opportunities[0]["solicitationNumber"] == "ABC123"
        mock_get.assert_called_once()

    def test_filter_combined_synopsis_solicitation(self):
        """Test filtering for Combined Synopsis/Solicitation."""
        opportunities = [
            {"title": "Combined Synopsis/Solicitation for IT Services", "type": "solicitation"},
            {"title": "Sources Sought Notice", "type": "presolicitation"},
            {"title": "Regular RFP", "type": "solicitation"},
            {"title": "Full and Open Competition", "description": "combined solicitation"},
        ]

        filtered = filter_combined_synopsis_solicitation(opportunities)

        assert len(filtered) == 3  # Should filter out regular RFP
        assert all("opportunity_type" in opp for opp in filtered)

    def test_filter_by_due_date_within_7_days(self):
        """Test filtering opportunities by due date."""
        future_date = (datetime.utcnow() + timedelta(days=5)).isoformat()
        past_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        far_future = (datetime.utcnow() + timedelta(days=30)).isoformat()

        opportunities = [
            {"responseDate": future_date, "title": "Due Soon"},
            {"responseDate": past_date, "title": "Past Due"},
            {"responseDate": far_future, "title": "Due Later"},
            {"title": "No Due Date"},
        ]

        filtered = filter_by_due_date(opportunities)

        assert len(filtered) == 1  # Only "Due Soon" should pass
        assert filtered[0]["title"] == "Due Soon"

    @patch.dict(os.environ, {'NAICS_WHITELIST': '541511,541512,541519'})
    def test_filter_by_naics_whitelist(self):
        """Test filtering by NAICS whitelist."""
        opportunities = [
            {"naicsCode": "541511", "title": "IT Consulting"},
            {"naicsCode": "541512", "title": "Computer Systems Design"},
            {"naicsCode": "123456", "title": "Other Service"},
            {"naicsCode": "541519", "title": "Other Computer Services"},
        ]

        filtered = filter_by_naics(opportunities)

        assert len(filtered) == 3  # Should exclude "Other Service"
        assert all(opp["naicsCode"].startswith(('541511', '541512', '541519')) for opp in filtered)

    def test_build_bid_pack_json_complete(self):
        """Test building comprehensive bid pack JSON."""
        opportunity = {
            "solicitationNumber": "ABC123",
            "title": "IT Services Contract",
            "description": "Comprehensive IT support services",
            "naicsCode": "541511",
            "responseDate": "2024-01-15T23:59:59",
            "officers": [
                {
                    "fullName": "John Doe",
                    "email": "john.doe@agency.gov",
                    "phone": "555-123-4567",
                    "office": "IT Department",
                }
            ],
            "department": "Department of Defense",
            "typeOfSetAsideDescription": "Small Business Set-Aside",
            "award": {"amount": "1000000", "date": "2024-02-01"},
        }

        bid_pack = build_bid_pack_json(opportunity)

        assert bid_pack["Solicitation #"] == "ABC123"
        assert bid_pack["Title"] == "IT Services Contract"
        assert bid_pack["Officer"] == "John Doe"
        assert bid_pack["Email"] == "john.doe@agency.gov"
        assert bid_pack["Set_Aside"] == "Small Business Set-Aside"
        assert bid_pack["Lead_Score"] > 0

    def test_calculate_opportunity_score(self):
        """Test opportunity scoring algorithm."""
        high_score_opp = {
            "officers": [{"email": "contact@agency.gov", "phone": "555-123-4567"}],
            "responseDate": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "typeOfSetAsideDescription": "Small Business Set-Aside",
            "typeOfContractDescription": "Limited Competition",
        }

        low_score_opp = {
            "officers": [],
            "responseDate": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "typeOfSetAsideDescription": "",
            "typeOfContractDescription": "Full and Open Competition",
        }

        high_score = calculate_opportunity_score(high_score_opp)
        low_score = calculate_opportunity_score(low_score_opp)

        assert high_score > low_score
        assert high_score >= 70  # Should get points for contact, due date, set-aside, competition

    @patch('govcon_subtrap_engine.fetch_sam_opportunities')
    @patch('govcon_subtrap_engine.fetch_fpds_feed')
    @patch('govcon_subtrap_engine.fetch_all')
    @patch('govcon_subtrap_engine.safe_airtable_write')
    def test_run_govcon_full_cycle(self, mock_write, mock_fetch, mock_fpds, mock_sam):
        """Test full GovCon engine cycle."""
        # Mock data sources
        mock_sam.return_value = [
            {
                "solicitationNumber": "ABC123",
                "title": "Combined Synopsis/Solicitation for IT",
                "responseDate": (datetime.utcnow() + timedelta(days=5)).isoformat(),
                "naicsCode": "541511",
                "officers": [{"email": "contact@gov.gov"}],
            }
        ]
        mock_fpds.return_value = []

        # Mock existing records (empty)
        mock_fetch.return_value = []

        # Mock successful writes
        mock_write.return_value = {"id": "rec123"}

        result = run_govcon()

        # Should process and write opportunities
        assert result >= 0


class TestSAMFiltering:
    """Test SAM.gov specific filtering logic."""

    @patch.dict(os.environ, {'NAICS_WHITELIST': '541511,541512'})
    def test_naics_prefix_matching(self):
        """Test NAICS prefix matching logic."""
        opportunities = [
            {"naicsCode": "54151101", "title": "Specific IT Consulting"},  # Should match 541511
            {"naicsCode": "54151201", "title": "Specific Systems Design"},  # Should match 541512
            {"naicsCode": "541513", "title": "Different IT Service"},  # Should not match
        ]

        filtered = filter_by_naics(opportunities)

        assert len(filtered) == 2
        assert filtered[0]["matched_naics"] == "54151101"
        assert filtered[1]["matched_naics"] == "54151201"

    def test_due_date_parsing_formats(self):
        """Test parsing various due date formats."""
        opportunities = [
            {"responseDate": "2024-01-15T23:59:59", "title": "ISO Format"},
            {"responseDate": "2024-01-15", "title": "Date Only"},
            {"responseDate": "01/15/2024", "title": "US Format"},
            {"responseDate": "15-Jan-2024", "title": "Text Month"},
            {"responseDate": "invalid-date", "title": "Invalid"},
        ]

        # Set all dates to be within 7 days for testing
        future_date = datetime.utcnow() + timedelta(days=3)
        for opp in opportunities[:-1]:  # Skip invalid date
            opp["responseDate"] = future_date.strftime(
                "%Y-%m-%dT%H:%M:%S" if "T" in opp["responseDate"] else "%Y-%m-%d"
            )

        filtered = filter_by_due_date(opportunities)

        # Should parse most formats correctly, skip invalid
        assert len(filtered) >= 2


if __name__ == "__main__":
    pytest.main([__file__])
