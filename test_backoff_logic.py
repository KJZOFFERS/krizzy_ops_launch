"""
Tests for backoff and retry logic.
"""
import pytest
import time
from unittest.mock import Mock, patch
from tenacity import RetryError
import requests


class TestBackoffLogic:
    """Test backoff and retry mechanisms."""
    
    def test_airtable_retry_on_429(self):
        """Test Airtable retry on rate limit (429)."""
        from airtable_utils import AirtableManager
        
        with patch.dict('os.environ', {
            'AIRTABLE_API_KEY': 'test_key',
            'AIRTABLE_BASE_ID': 'test_base'
        }):
            manager = AirtableManager()
            
            # Mock Table to raise 429 error first, then succeed
            with patch('airtable_utils.Table') as mock_table_class:
                mock_table = Mock()
                mock_table_class.return_value = mock_table
                
                # First call raises 429, second call succeeds
                mock_table.create.side_effect = [
                    requests.exceptions.HTTPError("429 Rate Limit"),
                    {'id': 'test_id'}
                ]
                
                with patch('airtable_utils.kpi_push') as mock_kpi:
                    success, record_id = manager.safe_airtable_write('TestTable', {'name': 'Test'})
                    
                    assert success is True
                    assert record_id == 'test_id'
                    assert mock_table.create.call_count == 2
                    # Should log rate limit error
                    mock_kpi.assert_called()
    
    def test_discord_retry_on_network_error(self):
        """Test Discord retry on network error."""
        from discord_utils import DiscordNotifier
        
        notifier = DiscordNotifier()
        
        with patch('requests.post') as mock_post:
            # First call fails, second call succeeds
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = [
                requests.exceptions.ConnectionError("Network error"),
                None
            ]
            mock_post.return_value = mock_response
            
            with patch.dict('os.environ', {'DISCORD_WEBHOOK_OPS': 'https://discord.com/webhook'}):
                with patch('discord_utils.kpi_push') as mock_kpi:
                    success = notifier.post_ops("Test message")
                    
                    assert success is True
                    assert mock_post.call_count == 2
                    mock_kpi.assert_called()
    
    def test_twilio_retry_on_30007(self):
        """Test Twilio retry on content error (30007)."""
        from twilio_utils import TwilioMessenger
        from twilio.base.exceptions import TwilioRestException
        
        with patch.dict('os.environ', {
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'TWILIO_MESSAGING_SERVICE_SID': 'test_service',
            'TWILIO_SAFE_MODE': 'false'
        }):
            messenger = TwilioMessenger()
            
            with patch.object(messenger.client.messages, 'create') as mock_create:
                # First call raises 30007, second call succeeds
                mock_create.side_effect = [
                    TwilioRestException(30007, "Content rotation needed", "https://api.twilio.com"),
                    Mock(sid='test_message_id')
                ]
                
                with patch('twilio_utils.kpi_push') as mock_kpi:
                    success, message_id = messenger.send_msg("+1234567890", "Test", "2024-01-01")
                    
                    assert success is True
                    assert message_id == 'test_message_id'
                    assert mock_create.call_count == 2
                    mock_kpi.assert_called()
    
    def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        from airtable_utils import AirtableManager
        
        with patch.dict('os.environ', {
            'AIRTABLE_API_KEY': 'test_key',
            'AIRTABLE_BASE_ID': 'test_base'
        }):
            manager = AirtableManager()
            
            with patch('airtable_utils.Table') as mock_table_class:
                mock_table = Mock()
                mock_table_class.return_value = mock_table
                mock_table.all.return_value = []
                # Always raise error
                mock_table.create.side_effect = requests.exceptions.HTTPError("500 Server Error")
                
                with patch('airtable_utils.kpi_push') as mock_kpi:
                    success, error = manager.safe_airtable_write('TestTable', {'name': 'Test'})
                    
                    assert success is False
                    assert "500 Server Error" in str(error)
                    # Should have retried 3 times
                    assert mock_table.create.call_count == 3
                    mock_kpi.assert_called()
    
    def test_exponential_backoff_timing(self):
        """Test that exponential backoff increases delay between retries."""
        from airtable_utils import AirtableManager
        
        with patch.dict('os.environ', {
            'AIRTABLE_API_KEY': 'test_key',
            'AIRTABLE_BASE_ID': 'test_base'
        }):
            manager = AirtableManager()
            
            with patch('airtable_utils.Table') as mock_table_class:
                mock_table = Mock()
                mock_table_class.return_value = mock_table
                mock_table.all.return_value = []
                mock_table.create.side_effect = requests.exceptions.HTTPError("429 Rate Limit")
                
                with patch('time.sleep') as mock_sleep:
                    with patch('airtable_utils.kpi_push'):
                        manager.safe_airtable_write('TestTable', {'name': 'Test'})
                        
                        # Should have called sleep with increasing delays
                        assert mock_sleep.call_count == 2  # 2 retries
                        # Check that delays are increasing (exponential backoff)
                        delays = [call[0][0] for call in mock_sleep.call_args_list]
                        assert delays[0] < delays[1]  # Second delay should be longer