"""Tests for airtable_utils module"""

import pytest
from unittest.mock import Mock, patch
from airtable_utils import safe_airtable_write, fetch_all, create_dedup_key, kpi_push


class TestAirtableUtils:
    """Test cases for Airtable utilities"""
    
    @patch('airtable_utils.AIRTABLE_API_KEY', 'test_key')
    @patch('airtable_utils.AIRTABLE_BASE_ID', 'test_base')
    @patch('airtable_utils.Table')
    def test_safe_airtable_write_success(self, mock_table_class):
        """Test successful Airtable write"""
        # Setup
        mock_table = Mock()
        mock_table.create.return_value = {"id": "test_id", "fields": {"Test": "data"}}
        mock_table_class.return_value = mock_table
        
        # Test
        result = safe_airtable_write("TestTable", {"Test": "data"})
        
        # Assertions
        assert result == {"id": "test_id", "fields": {"Test": "data"}}
        mock_table.create.assert_called_once_with({"Test": "data"})
    
    @patch('airtable_utils.AIRTABLE_API_KEY', 'test_key')
    @patch('airtable_utils.AIRTABLE_BASE_ID', 'test_base')
    @patch('airtable_utils.Table')
    def test_safe_airtable_write_with_upsert(self, mock_table_class):
        """Test Airtable write with upsert functionality"""
        # Setup
        mock_table = Mock()
        mock_table.all.return_value = [
            {"id": "existing_id", "fields": {"Key": "existing_value"}}
        ]
        mock_table.update.return_value = {"id": "existing_id", "fields": {"Key": "new_value"}}
        mock_table_class.return_value = mock_table
        
        # Test
        result = safe_airtable_write("TestTable", {"Key": "new_value"}, ["Key"])
        
        # Assertions
        assert result == {"id": "existing_id", "fields": {"Key": "new_value"}}
        mock_table.update.assert_called_once_with("existing_id", {"Key": "new_value"})
    
    @patch('airtable_utils.AIRTABLE_API_KEY', 'test_key')
    @patch('airtable_utils.AIRTABLE_BASE_ID', 'test_base')
    @patch('airtable_utils.Table')
    def test_safe_airtable_write_retry_logic(self, mock_table_class):
        """Test retry logic on Airtable write failure"""
        # Setup
        mock_table = Mock()
        mock_table.create.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            {"id": "test_id", "fields": {"Test": "data"}}
        ]
        mock_table_class.return_value = mock_table
        
        # Test
        result = safe_airtable_write("TestTable", {"Test": "data"})
        
        # Assertions
        assert result == {"id": "test_id", "fields": {"Test": "data"}}
        assert mock_table.create.call_count == 3
    
    @patch('airtable_utils.AIRTABLE_API_KEY', 'test_key')
    @patch('airtable_utils.AIRTABLE_BASE_ID', 'test_base')
    @patch('airtable_utils.Table')
    def test_fetch_all_success(self, mock_table_class):
        """Test successful Airtable fetch"""
        # Setup
        mock_table = Mock()
        mock_table.all.return_value = [{"id": "1", "fields": {"Test": "data"}}]
        mock_table_class.return_value = mock_table
        
        # Test
        result = fetch_all("TestTable")
        
        # Assertions
        assert result == [{"id": "1", "fields": {"Test": "data"}}]
        mock_table.all.assert_called_once()
    
    def test_create_dedup_key(self):
        """Test deduplication key creation"""
        # Test with phone and email
        record = {
            "Phone": "+1234567890",
            "Email": "test@example.com",
            "Source_URL": "https://example.com"
        }
        
        key = create_dedup_key(record, ["Phone", "Email", "Source_URL"])
        
        # Should create consistent hash for phone/email
        assert "|" in key
        assert len(key.split("|")) == 3
    
    @patch('airtable_utils.safe_airtable_write')
    def test_kpi_push_success(self, mock_safe_write):
        """Test KPI push functionality"""
        # Setup
        mock_safe_write.return_value = {"id": "kpi_id"}
        
        # Test
        kpi_push("test_event", {"count": 5, "status": "success"})
        
        # Assertions
        mock_safe_write.assert_called_once()
        call_args = mock_safe_write.call_args
        assert call_args[0][0] == "KPI_Log"
        assert "Event" in call_args[0][1]
        assert call_args[0][1]["Event"] == "test_event"
    
    @patch('airtable_utils.safe_airtable_write')
    def test_kpi_push_failure_handling(self, mock_safe_write):
        """Test KPI push failure handling"""
        # Setup
        mock_safe_write.side_effect = Exception("Airtable error")
        
        # Test - should not raise exception
        kpi_push("test_event", {"count": 5})
        
        # Assertions
        mock_safe_write.assert_called_once()