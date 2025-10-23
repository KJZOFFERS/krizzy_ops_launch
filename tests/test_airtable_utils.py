"""Tests for Airtable utilities."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import HTTPError
from airtable_utils import (
    safe_airtable_write,
    fetch_all,
    add_record,
    _exponential_backoff_with_jitter,
    _should_retry,
    _hash_key,
)


def test_hash_key():
    """Test hash key generation is consistent."""
    value = "test@example.com"
    hash1 = _hash_key(value)
    hash2 = _hash_key(value)
    assert hash1 == hash2
    assert len(hash1) == 16


def test_should_retry_429():
    """Test retry logic for 429 status code."""
    mock_response = Mock()
    mock_response.status_code = 429
    error = HTTPError()
    error.response = mock_response
    assert _should_retry(error) is True


def test_should_retry_500():
    """Test retry logic for 500 status code."""
    mock_response = Mock()
    mock_response.status_code = 500
    error = HTTPError()
    error.response = mock_response
    assert _should_retry(error) is True


def test_should_retry_400():
    """Test no retry for 400 status code."""
    mock_response = Mock()
    mock_response.status_code = 400
    error = HTTPError()
    error.response = mock_response
    assert _should_retry(error) is False


def test_exponential_backoff_with_jitter():
    """Test backoff calculation."""
    delay1 = _exponential_backoff_with_jitter(0)
    delay2 = _exponential_backoff_with_jitter(1)
    delay3 = _exponential_backoff_with_jitter(10)

    assert 1.0 <= delay1 <= 1.2
    assert 2.0 <= delay2 <= 2.4
    assert delay3 <= 32.0


@patch("airtable_utils.AIRTABLE_API_KEY", "test_key")
@patch("airtable_utils.AIRTABLE_BASE_ID", "test_base")
@patch("airtable_utils.Table")
def test_safe_airtable_write_create(mock_table_class):
    """Test safe_airtable_write creates new record."""
    mock_table = MagicMock()
    mock_table.all.return_value = []
    mock_table.create.return_value = {"id": "rec123", "fields": {"test": "data"}}
    mock_table_class.return_value = mock_table

    record = {"test": "data"}
    result = safe_airtable_write("TestTable", record, ["test"])

    assert result is not None
    assert result["id"] == "rec123"
    mock_table.create.assert_called_once()


@patch("airtable_utils.AIRTABLE_API_KEY", "test_key")
@patch("airtable_utils.AIRTABLE_BASE_ID", "test_base")
@patch("airtable_utils.Table")
def test_safe_airtable_write_update(mock_table_class):
    """Test safe_airtable_write updates existing record."""
    mock_table = MagicMock()
    existing_record = {"id": "rec123", "fields": {"_dedupe_key": "test_hash"}}
    mock_table.all.return_value = [existing_record]
    mock_table.update.return_value = {"id": "rec123", "fields": {"test": "updated"}}
    mock_table_class.return_value = mock_table

    record = {"test": "updated"}
    result = safe_airtable_write("TestTable", record, ["test"])

    assert result is not None
    assert result["id"] == "rec123"
    mock_table.update.assert_called_once()


@patch("airtable_utils.AIRTABLE_API_KEY", "test_key")
@patch("airtable_utils.AIRTABLE_BASE_ID", "test_base")
@patch("airtable_utils.Table")
@patch("airtable_utils.time.sleep")
def test_safe_airtable_write_retry_on_429(mock_sleep, mock_table_class):
    """Test safe_airtable_write retries on 429."""
    mock_table = MagicMock()
    mock_table.all.return_value = []

    mock_response = Mock()
    mock_response.status_code = 429
    error = HTTPError()
    error.response = mock_response

    mock_table.create.side_effect = [
        error,
        {"id": "rec123", "fields": {"test": "data"}}
    ]
    mock_table_class.return_value = mock_table

    record = {"test": "data"}
    result = safe_airtable_write("TestTable", record, ["test"])

    assert result is not None
    assert mock_table.create.call_count == 2
    mock_sleep.assert_called()


@patch("airtable_utils.AIRTABLE_API_KEY", "")
@patch("airtable_utils.AIRTABLE_BASE_ID", "")
def test_safe_airtable_write_no_credentials():
    """Test safe_airtable_write returns None without credentials."""
    result = safe_airtable_write("TestTable", {"test": "data"}, ["test"])
    assert result is None


@patch("airtable_utils.AIRTABLE_API_KEY", "test_key")
@patch("airtable_utils.AIRTABLE_BASE_ID", "test_base")
@patch("airtable_utils.Table")
def test_fetch_all(mock_table_class):
    """Test fetch_all returns all records."""
    mock_table = MagicMock()
    mock_records = [
        {"id": "rec1", "fields": {"name": "test1"}},
        {"id": "rec2", "fields": {"name": "test2"}},
    ]
    mock_table.all.return_value = mock_records
    mock_table_class.return_value = mock_table

    result = fetch_all("TestTable")

    assert len(result) == 2
    assert result[0]["id"] == "rec1"
    assert result[1]["id"] == "rec2"


@patch("airtable_utils.AIRTABLE_API_KEY", "test_key")
@patch("airtable_utils.AIRTABLE_BASE_ID", "test_base")
@patch("airtable_utils.Table")
def test_add_record(mock_table_class):
    """Test add_record creates new record."""
    mock_table = MagicMock()
    mock_table.create.return_value = {"id": "rec123", "fields": {"test": "data"}}
    mock_table_class.return_value = mock_table

    result = add_record("TestTable", {"test": "data"})

    assert result is not None
    assert result["id"] == "rec123"
    mock_table.create.assert_called_once()
