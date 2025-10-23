"""Tests for GovCon opportunity engine."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock
from govcon_subtrap_engine import (
    _is_within_7_days,
    _matches_naics,
    _is_combined_synopsis,
    build_bid_pack,
)


def test_is_within_7_days_valid():
    """Test due date within 7 days."""
    future_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    assert _is_within_7_days(future_date) is True


def test_is_within_7_days_too_far():
    """Test due date beyond 7 days."""
    future_date = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    assert _is_within_7_days(future_date) is False


def test_is_within_7_days_past():
    """Test past due date."""
    past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert _is_within_7_days(past_date) is False


def test_is_within_7_days_invalid():
    """Test invalid date string."""
    assert _is_within_7_days("invalid") is False
    assert _is_within_7_days("") is False


def test_matches_naics_valid():
    """Test NAICS code matches whitelist."""
    with patch("govcon_subtrap_engine.NAICS_WHITELIST", ["541", "334", "541512"]):
        assert _matches_naics("541512") is True
        assert _matches_naics("541") is True
        assert _matches_naics("334") is True


def test_matches_naics_invalid():
    """Test NAICS code doesn't match whitelist."""
    with patch("govcon_subtrap_engine.NAICS_WHITELIST", ["541", "334"]):
        assert _matches_naics("999") is False
        assert _matches_naics("123") is False


def test_is_combined_synopsis_valid():
    """Test Combined Synopsis/Solicitation detection."""
    assert _is_combined_synopsis("Combined Synopsis/Solicitation") is True
    assert _is_combined_synopsis("Presolicitation") is True
    assert _is_combined_synopsis("Solicitation") is True


def test_is_combined_synopsis_invalid():
    """Test non-Combined Synopsis detection."""
    assert _is_combined_synopsis("Award Notice") is False
    assert _is_combined_synopsis("Intent to Bundle") is False


def test_build_bid_pack():
    """Test bid pack JSON building."""
    with patch("govcon_subtrap_engine.UEI", "TEST_UEI"), \
         patch("govcon_subtrap_engine.CAGE_CODE", "TEST_CAGE"):
        opp = {
            "solicitationNumber": "SOL123",
            "title": "Test Opportunity",
            "naicsCode": "541512",
            "responseDeadLine": "2025-10-25T00:00:00Z",
            "type": "Combined Synopsis/Solicitation",
            "uiLink": "https://sam.gov/test",
            "description": "Test description",
            "pointOfContact": [
                {
                    "fullName": "John Doe",
                    "email": "john@example.com",
                    "phone": "555-1234"
                }
            ]
        }

        bid_pack = build_bid_pack(opp)

        assert bid_pack["Solicitation_Number"] == "SOL123"
        assert bid_pack["Title"] == "Test Opportunity"
        assert bid_pack["NAICS"] == "541512"
        assert bid_pack["Officer_Name"] == "John Doe"
        assert bid_pack["Officer_Email"] == "john@example.com"
        assert bid_pack["UEI"] == "TEST_UEI"
        assert bid_pack["CAGE_CODE"] == "TEST_CAGE"


@patch.dict("os.environ", {"SAM_SEARCH_API": "", "FPDS_ATOM_FEED": ""})
@patch("govcon_subtrap_engine.fetch_sam_opportunities")
@patch("govcon_subtrap_engine.fetch_fpds_opportunities")
@patch("govcon_subtrap_engine.safe_airtable_write")
@patch("govcon_subtrap_engine.post_ops")
@patch("govcon_subtrap_engine.kpi")
def test_run_govcon_no_data(mock_kpi, mock_post_ops, mock_write, mock_fpds, mock_sam):
    """Test run_govcon with no data."""
    mock_sam.return_value = []
    mock_fpds.return_value = []

    from govcon_subtrap_engine import run_govcon
    count = run_govcon()

    assert count == 0
    mock_kpi.kpi_push.assert_called()
