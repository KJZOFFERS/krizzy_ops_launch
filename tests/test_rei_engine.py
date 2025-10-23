"""Tests for REI disposition engine."""

import pytest
from unittest.mock import patch, Mock
from rei_dispo_engine import _hash_contact, parse_zillow, parse_craigslist


def test_hash_contact_with_both():
    """Test contact hash with phone and email."""
    hash1 = _hash_contact("555-1234", "test@example.com")
    hash2 = _hash_contact("555-1234", "test@example.com")
    assert hash1 == hash2
    assert len(hash1) == 16


def test_hash_contact_with_phone_only():
    """Test contact hash with phone only."""
    hash1 = _hash_contact("555-1234", "")
    hash2 = _hash_contact("555-1234", "")
    assert hash1 == hash2


def test_hash_contact_with_email_only():
    """Test contact hash with email only."""
    hash1 = _hash_contact("", "test@example.com")
    hash2 = _hash_contact("", "test@example.com")
    assert hash1 == hash2


def test_hash_contact_different():
    """Test different contacts have different hashes."""
    hash1 = _hash_contact("555-1234", "test1@example.com")
    hash2 = _hash_contact("555-5678", "test2@example.com")
    assert hash1 != hash2


@patch("rei_dispo_engine.requests.get")
@patch("rei_dispo_engine.post_err")
@patch("rei_dispo_engine.kpi")
def test_parse_zillow_success(mock_kpi, mock_post_err, mock_get):
    """Test Zillow parsing success."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "props": [
            {
                "zpid": "12345",
                "address": "123 Main St",
                "city": "TestCity",
                "state": "CA",
                "zipcode": "12345",
                "price": 500000,
                "brokerName": "Test Broker",
                "brokerPhone": "555-1234",
                "brokerEmail": "broker@example.com",
                "detailUrl": "/homedetails/123"
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    leads = parse_zillow()

    assert len(leads) == 1
    assert leads[0]["Address"] == "123 Main St"
    assert leads[0]["Phone"] == "555-1234"
    assert leads[0]["Email"] == "broker@example.com"
    assert leads[0]["Source"] == "Zillow"


@patch("rei_dispo_engine.requests.get")
@patch("rei_dispo_engine.post_err")
@patch("rei_dispo_engine.kpi")
def test_parse_zillow_failure(mock_kpi, mock_post_err, mock_get):
    """Test Zillow parsing failure."""
    mock_get.side_effect = Exception("Connection error")

    leads = parse_zillow()

    assert leads == []
    mock_post_err.assert_called_once()
    mock_kpi.kpi_push.assert_called_once()


@patch("rei_dispo_engine.requests.get")
@patch("rei_dispo_engine.post_err")
@patch("rei_dispo_engine.kpi")
def test_parse_craigslist_failure(mock_kpi, mock_post_err, mock_get):
    """Test Craigslist parsing failure."""
    mock_get.side_effect = Exception("Connection error")

    leads = parse_craigslist()

    assert leads == []
    mock_post_err.assert_called_once()
    mock_kpi.kpi_push.assert_called_once()


@patch("rei_dispo_engine.parse_zillow")
@patch("rei_dispo_engine.parse_craigslist")
@patch("rei_dispo_engine.safe_airtable_write")
@patch("rei_dispo_engine.post_ops")
@patch("rei_dispo_engine.kpi")
def test_run_rei(mock_kpi, mock_post_ops, mock_write, mock_cl, mock_zillow):
    """Test run_rei function."""
    mock_zillow.return_value = [
        {
            "source_id": "123",
            "contact_hash": "abc123",
            "Address": "123 Main St",
            "Phone": "555-1234",
            "Email": "test@example.com"
        }
    ]
    mock_cl.return_value = []
    mock_write.return_value = {"id": "rec123"}

    from rei_dispo_engine import run_rei
    count = run_rei()

    assert count == 1
    mock_write.assert_called_once()
    mock_post_ops.assert_called_once()
    assert mock_kpi.kpi_push.call_count == 2
