"""
Tests for airtable_utils module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from airtable_utils import AirtableManager, safe_airtable_write, fetch_all


class TestAirtableManager:
    """Test AirtableManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch.dict('os.environ', {
            'AIRTABLE_API_KEY': 'test_key',
            'AIRTABLE_BASE_ID': 'test_base'
        }):
            self.manager = AirtableManager()
    
    def test_init_missing_credentials(self):
        """Test initialization with missing credentials."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set"):
                AirtableManager()
    
    @patch('airtable_utils.Table')
    def test_safe_airtable_write_new_record(self, mock_table_class):
        """Test writing a new record."""
        mock_table = Mock()
        mock_table_class.return_value = mock_table
        mock_table.all.return_value = []  # No existing records
        mock_table.create.return_value = {'id': 'test_id'}
        
        record = {'name': 'Test', 'email': 'test@example.com'}
        success, record_id = self.manager.safe_airtable_write('TestTable', record)
        
        assert success is True
        assert record_id == 'test_id'
        mock_table.create.assert_called_once()
    
    @patch('airtable_utils.Table')
    def test_safe_airtable_write_existing_record(self, mock_table_class):
        """Test updating an existing record."""
        mock_table = Mock()
        mock_table_class.return_value = mock_table
        mock_table.all.return_value = [{'id': 'existing_id', 'fields': {'dedup_key': 'test_hash'}}]
        mock_table.update.return_value = {'id': 'existing_id'}
        
        record = {'name': 'Test', 'email': 'test@example.com', 'dedup_key': 'test_hash'}
        success, record_id = self.manager.safe_airtable_write('TestTable', record)
        
        assert success is True
        assert record_id == 'existing_id'
        mock_table.update.assert_called_once()
    
    def test_generate_dedup_key(self):
        """Test deduplication key generation."""
        record = {'name': 'Test', 'email': 'test@example.com'}
        key = self.manager._generate_dedup_key(record, ['name', 'email'])
        
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length
    
    @patch('airtable_utils.Table')
    def test_fetch_all_success(self, mock_table_class):
        """Test successful fetch_all."""
        mock_table = Mock()
        mock_table_class.return_value = mock_table
        mock_table.all.return_value = [{'id': '1', 'fields': {'name': 'Test'}}]
        
        records = self.manager.fetch_all('TestTable')
        
        assert len(records) == 1
        assert records[0]['fields']['name'] == 'Test'
    
    @patch('airtable_utils.Table')
    def test_fetch_all_error(self, mock_table_class):
        """Test fetch_all with error."""
        mock_table = Mock()
        mock_table_class.return_value = mock_table
        mock_table.all.side_effect = Exception("API Error")
        
        with patch('airtable_utils.kpi_push') as mock_kpi:
            records = self.manager.fetch_all('TestTable')
            
            assert records == []
            mock_kpi.assert_called_once()


class TestSafeAirtableWrite:
    """Test safe_airtable_write function."""
    
    @patch('airtable_utils.airtable')
    def test_safe_airtable_write_success(self, mock_airtable):
        """Test successful safe_airtable_write."""
        mock_airtable.safe_airtable_write.return_value = (True, 'test_id')
        
        success, record_id = safe_airtable_write('TestTable', {'name': 'Test'})
        
        assert success is True
        assert record_id == 'test_id'
        mock_airtable.safe_airtable_write.assert_called_once_with('TestTable', {'name': 'Test'}, None)


class TestFetchAll:
    """Test fetch_all function."""
    
    @patch('airtable_utils.airtable')
    def test_fetch_all_success(self, mock_airtable):
        """Test successful fetch_all."""
        mock_airtable.fetch_all.return_value = [{'id': '1', 'fields': {'name': 'Test'}}]
        
        records = fetch_all('TestTable')
        
        assert len(records) == 1
        mock_airtable.fetch_all.assert_called_once_with('TestTable', None)