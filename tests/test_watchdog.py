"""Tests for watchdog functionality."""

import pytest
from unittest.mock import patch, Mock
from watchdog import (
    rotate_proxy,
    throttle_on_429,
    validate_data_integrity,
)


@patch("watchdog.PROXY_ROTATION_ENABLED", True)
@patch("watchdog.PROXY_LIST", ["http://proxy1.com", "http://proxy2.com", "http://proxy3.com"])
@patch("watchdog.kpi")
def test_rotate_proxy(mock_kpi):
    """Test proxy rotation."""
    import os

    rotate_proxy()

    proxy_list = ["http://proxy1.com", "http://proxy2.com", "http://proxy3.com"]
    assert os.environ.get("HTTP_PROXY") in proxy_list
    mock_kpi.kpi_push.assert_called_once()


@patch("watchdog.time.sleep")
@patch("watchdog.post_ops")
@patch("watchdog.kpi")
def test_throttle_on_429(mock_kpi, mock_post_ops, mock_sleep):
    """Test throttling on rate limit."""
    throttle_on_429(60)

    mock_sleep.assert_called_once_with(60)
    mock_post_ops.assert_called_once()
    mock_kpi.kpi_push.assert_called_once()


@patch("watchdog.fetch_all")
@patch("watchdog.post_err")
@patch("watchdog.kpi")
def test_validate_data_integrity_success(mock_kpi, mock_post_err, mock_fetch):
    """Test data integrity validation success."""
    mock_fetch.side_effect = [
        [
            {"fields": {"Source_URL": "http://test.com", "Phone": "555-1234"}},
            {"fields": {"Source_URL": "http://test2.com", "Email": "test@example.com"}},
        ],
        [
            {"fields": {
                "Solicitation_Number": "SOL123",
                "Officer_Email": "officer@example.com"
            }},
        ],
    ]

    results = validate_data_integrity()

    assert results["tables_checked"] == 2
    assert results["invalid_records"] == 0
    assert results["missing_required_fields"] == 0


@patch("watchdog.fetch_all")
@patch("watchdog.post_err")
@patch("watchdog.kpi")
def test_validate_data_integrity_with_invalid(mock_kpi, mock_post_err, mock_fetch):
    """Test data integrity validation with invalid records."""
    mock_fetch.side_effect = [
        [
            {"fields": {"Source_URL": "http://test.com"}},
            {"fields": {}},
        ],
        [
            {"fields": {"Solicitation_Number": "SOL123"}},
        ],
    ]

    results = validate_data_integrity()

    assert results["tables_checked"] == 2
    assert results["invalid_records"] >= 1
    assert results["missing_required_fields"] >= 1
