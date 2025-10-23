import os
from unittest.mock import Mock, patch

import pytest

from airtable_utils import _get_table, add_record, fetch_all, kpi_push, safe_airtable_write


class TestAirtableUtils:
    """Test suite for airtable_utils module."""

    @patch.dict(os.environ, {'AIRTABLE_API_KEY': 'test_key', 'AIRTABLE_BASE_ID': 'test_base'})
    def test_get_table_success(self):
        """Test successful table creation."""
        with patch('airtable_utils.Table') as mock_table:
            table = _get_table("test_table")
            mock_table.assert_called_once_with('test_key', 'test_base', 'test_table')

    def test_get_table_missing_credentials(self):
        """Test table creation with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing AIRTABLE_API_KEY"):
                _get_table("test_table")

    @patch('airtable_utils._get_table')
    def test_safe_airtable_write_new_record(self, mock_get_table):
        """Test writing new record to Airtable."""
        # Setup mock table
        mock_table = Mock()
        mock_table.all.return_value = []  # No existing records
        mock_table.create.return_value = {"id": "rec123", "fields": {"test": "data"}}
        mock_get_table.return_value = mock_table

        # Test data
        record = {"Phone": "1234567890", "Email": "test@example.com", "Name": "Test"}
        key_fields = ["Phone", "Email"]

        result = safe_airtable_write("test_table", record, key_fields)

        # Assertions
        assert result is not None
        assert result["id"] == "rec123"
        mock_table.create.assert_called_once()

        # Check that dedup_key was added
        created_record = mock_table.create.call_args[0][0]
        assert "dedup_key" in created_record

    @patch('airtable_utils._get_table')
    def test_safe_airtable_write_update_existing(self, mock_get_table):
        """Test updating existing record in Airtable."""
        # Setup mock table
        mock_table = Mock()
        existing_record = {"id": "rec123", "fields": {"dedup_key": "test_key"}}
        mock_table.all.return_value = [existing_record]
        mock_table.update.return_value = {"id": "rec123", "fields": {"updated": True}}
        mock_get_table.return_value = mock_table

        # Test data
        record = {"Phone": "1234567890", "Email": "test@example.com", "Name": "Updated"}
        key_fields = ["Phone", "Email"]

        result = safe_airtable_write("test_table", record, key_fields)

        # Assertions
        assert result is not None
        mock_table.update.assert_called_once_with("rec123", record)
        mock_table.create.assert_not_called()

    @patch('airtable_utils._get_table')
    def test_safe_airtable_write_error_handling(self, mock_get_table):
        """Test error handling in safe_airtable_write."""
        # Setup mock table to raise exception
        mock_table = Mock()
        mock_table.all.side_effect = Exception("API Error")
        mock_get_table.return_value = mock_table

        record = {"test": "data"}
        key_fields = ["test"]

        result = safe_airtable_write("test_table", record, key_fields)

        # Should return None on error
        assert result is None

    @patch('airtable_utils._get_table')
    def test_fetch_all_success(self, mock_get_table):
        """Test successful fetch_all operation."""
        # Setup mock table
        mock_table = Mock()
        expected_records = [{"id": "rec1"}, {"id": "rec2"}]
        mock_table.all.return_value = expected_records
        mock_get_table.return_value = mock_table

        result = fetch_all("test_table")

        assert result == expected_records
        mock_table.all.assert_called_once()

    @patch('airtable_utils._get_table')
    def test_fetch_all_error_handling(self, mock_get_table):
        """Test error handling in fetch_all."""
        # Setup mock table to raise exception
        mock_table = Mock()
        mock_table.all.side_effect = Exception("API Error")
        mock_get_table.return_value = mock_table

        result = fetch_all("test_table")

        # Should return empty list on error
        assert result == []

    @patch('airtable_utils.safe_airtable_write')
    def test_kpi_push_success(self, mock_write):
        """Test successful KPI push."""
        mock_write.return_value = {"id": "rec123"}

        kpi_push("test_event", {"count": 5, "status": "success"})

        # Check that safe_airtable_write was called with correct data
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0]

        assert call_args[0] == "KPI_Log"  # table name
        assert call_args[2] == ["Event", "Timestamp"]  # key fields

        record = call_args[1]
        assert record["Event"] == "test_event"
        assert record["Count"] == 5
        assert record["Status"] == "success"
        assert "Timestamp" in record

    @patch('airtable_utils.safe_airtable_write')
    def test_add_record_legacy_function(self, mock_write):
        """Test legacy add_record function."""
        mock_write.return_value = {"id": "rec123"}

        test_data = {"Name": "Test", "Phone": "1234567890"}
        result = add_record("test_table", test_data)

        # Should call safe_airtable_write with default key fields
        mock_write.assert_called_once_with(
            "test_table", test_data, ["Source_URL", "Phone", "Email"]
        )
        assert result == {"id": "rec123"}


class TestBackoffLogic:
    """Test backoff and retry logic."""

    @patch('airtable_utils._get_table')
    def test_backoff_on_rate_limit(self, mock_get_table):
        """Test that backoff works on rate limit errors."""
        mock_table = Mock()
        # First call fails with 429, second succeeds
        mock_table.all.side_effect = [Exception("429 Rate Limited"), [{"id": "rec1"}]]
        mock_get_table.return_value = mock_table

        # This should retry and eventually succeed
        result = fetch_all("test_table")

        # Should have been called twice due to retry
        assert mock_table.all.call_count == 2
        assert result == [{"id": "rec1"}]

    @patch('airtable_utils._get_table')
    def test_backoff_gives_up_on_client_error(self, mock_get_table):
        """Test that backoff gives up on client errors."""
        mock_table = Mock()
        # Always fails with 400 error
        mock_table.all.side_effect = Exception("400 Bad Request")
        mock_get_table.return_value = mock_table

        result = fetch_all("test_table")

        # Should return empty list after giving up
        assert result == []


class TestDataValidation:
    """Test data validation and sanitization."""

    def test_phone_email_hashing(self):
        """Test that PII fields are properly hashed."""
        with patch('airtable_utils._get_table') as mock_get_table:
            mock_table = Mock()
            mock_table.all.return_value = []
            mock_table.create.return_value = {"id": "rec123"}
            mock_get_table.return_value = mock_table

            record = {"Phone": "1234567890", "Email": "test@example.com"}
            key_fields = ["Phone", "Email"]

            safe_airtable_write("test_table", record, key_fields)

            # Check that dedup_key contains hashed values
            created_record = mock_table.create.call_args[0][0]
            dedup_key = created_record["dedup_key"]

            # Should not contain raw phone or email
            assert "1234567890" not in dedup_key
            assert "test@example.com" not in dedup_key
            # Should contain some hash-like string
            assert len(dedup_key) > 10


if __name__ == "__main__":
    pytest.main([__file__])
