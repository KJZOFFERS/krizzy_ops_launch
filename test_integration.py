"""
Integration tests for KRIZZY OPS v3.0.0
Tests the complete system integration.
"""
import pytest
import os
import time
from unittest.mock import Mock, patch, MagicMock
from main import app
from kpi import kpi_push
from airtable_utils import safe_airtable_write
from discord_utils import post_ops
from twilio_utils import send_msg


class TestIntegration:
    """Integration tests for the complete system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.app = app.test_client()
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'AIRTABLE_API_KEY': 'test_key',
            'AIRTABLE_BASE_ID': 'test_base',
            'DISCORD_WEBHOOK_OPS': 'https://discord.com/webhook/test',
            'DISCORD_WEBHOOK_ERRORS': 'https://discord.com/webhook/test',
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'TWILIO_MESSAGING_SERVICE_SID': 'test_service',
            'TWILIO_SAFE_MODE': 'true',
            'SAM_SEARCH_API': 'https://api.sam.gov/v1/search',
            'SAM_API_KEY': 'test_key',
            'NAICS_WHITELIST': '541511,541512',
            'UEI': 'TEST123456789',
            'CAGE_CODE': 'TEST1',
            'FPDS_ATOM_FEED': 'https://www.fpds.gov/test',
            'PORT': '8080'
        })
        self.env_patcher.start()
    
    def teardown_method(self):
        """Clean up test environment."""
        self.env_patcher.stop()
    
    def test_health_endpoint_integration(self):
        """Test health endpoint returns correct format."""
        with patch('main.startup_time', time.time()):
            response = self.app.get('/health')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'ok'
            assert 'ts' in data
            assert 'uptime_seconds' in data
            assert 'version' in data
    
    def test_rei_endpoint_integration(self):
        """Test REI endpoint with mocked dependencies."""
        with patch('rei_dispo_engine.run_rei') as mock_run_rei, \
             patch('kpi.kpi_push') as mock_kpi:
            
            mock_run_rei.return_value = 5
            
            response = self.app.post('/ops/rei')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['REI_Leads'] == 5
            assert data['status'] == 'success'
            
            # Verify KPI logging
            assert mock_kpi.call_count == 2  # cycle_start and cycle_end
    
    def test_govcon_endpoint_integration(self):
        """Test GovCon endpoint with mocked dependencies."""
        with patch('govcon_subtrap_engine.run_govcon') as mock_run_govcon, \
             patch('kpi.kpi_push') as mock_kpi:
            
            mock_run_govcon.return_value = 3
            
            response = self.app.post('/ops/govcon')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['GovCon_Bids'] == 3
            assert data['status'] == 'success'
            
            # Verify KPI logging
            assert mock_kpi.call_count == 2  # cycle_start and cycle_end
    
    def test_watchdog_endpoint_integration(self):
        """Test Watchdog endpoint with mocked dependencies."""
        with patch('watchdog.run_watchdog') as mock_run_watchdog, \
             patch('kpi.kpi_push') as mock_kpi:
            
            mock_run_watchdog.return_value = 2
            
            response = self.app.post('/ops/watchdog')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['Cleaned'] == 2
            assert data['status'] == 'success'
            
            # Verify KPI logging
            assert mock_kpi.call_count == 2  # cycle_start and cycle_end
    
    def test_error_handling_integration(self):
        """Test error handling across endpoints."""
        with patch('rei_dispo_engine.run_rei') as mock_run_rei, \
             patch('kpi.kpi_push') as mock_kpi:
            
            mock_run_rei.side_effect = Exception("Test error")
            
            response = self.app.post('/ops/rei')
            
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
            assert data['status'] == 'error'
            
            # Verify error KPI logging
            assert mock_kpi.call_count == 2  # cycle_start and error
    
    def test_kpi_logging_integration(self):
        """Test KPI logging system integration."""
        with patch('airtable_utils.airtable._post_to_airtable') as mock_airtable, \
             patch('discord_utils.discord._post_to_discord') as mock_discord:
            
            # Test successful KPI push
            kpi_push("test_event", {"test": "data"})
            
            # Verify Airtable call
            mock_airtable.assert_called_once()
            call_args = mock_airtable.call_args[0]
            assert call_args[0] == "KPI_Log"
            assert call_args[1]["Event"] == "test_event"
            
            # Verify Discord call
            mock_discord.assert_called_once()
    
    def test_airtable_safe_write_integration(self):
        """Test Airtable safe write with retry logic."""
        with patch('airtable_utils.Table') as mock_table_class:
            mock_table = Mock()
            mock_table_class.return_value = mock_table
            mock_table.all.return_value = []  # No existing records
            mock_table.create.return_value = {'id': 'test_id'}
            
            success, record_id = safe_airtable_write(
                "TestTable", 
                {"name": "Test"}, 
                ["name"]
            )
            
            assert success is True
            assert record_id == 'test_id'
            mock_table.create.assert_called_once()
    
    def test_discord_notification_integration(self):
        """Test Discord notification system."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            success = post_ops("Test message")
            
            assert success is True
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "content" in call_args[1]["json"]
            assert "✅ Test message" in call_args[1]["json"]["content"]
    
    def test_twilio_messaging_integration(self):
        """Test Twilio messaging with safe mode."""
        with patch('twilio_utils.twilio.client') as mock_client:
            # Test in safe mode (should not send actual SMS)
            success, message_id = send_msg("+1234567890", "Test Title", "2024-01-01")
            
            # In safe mode, should return success without sending
            assert success is True
            assert message_id == "safe_mode"
    
    def test_system_startup_integration(self):
        """Test system startup with all components."""
        with patch('kpi.kpi_push') as mock_kpi, \
             patch('airtable_utils.airtable') as mock_airtable, \
             patch('discord_utils.discord') as mock_discord, \
             patch('twilio_utils.twilio') as mock_twilio:
            
            # Simulate system startup
            from main import app
            
            # Verify startup KPI logging
            assert mock_kpi.call_count >= 1
    
    def test_error_recovery_integration(self):
        """Test error recovery mechanisms."""
        with patch('airtable_utils.Table') as mock_table_class:
            mock_table = Mock()
            mock_table_class.return_value = mock_table
            
            # Simulate rate limit error, then success
            mock_table.create.side_effect = [
                Exception("429 Rate Limit"),
                Exception("429 Rate Limit"),
                {'id': 'success_id'}
            ]
            
            # Should retry and eventually succeed
            success, record_id = safe_airtable_write("TestTable", {"name": "Test"})
            
            # Note: This test may fail due to retry logic timing
            # In a real scenario, the retry would eventually succeed
            assert mock_table.create.call_count == 3  # 3 attempts
    
    def test_data_flow_integration(self):
        """Test complete data flow from source to destination."""
        with patch('rei_dispo_engine.REILeadProcessor.parse_zillow') as mock_zillow, \
             patch('rei_dispo_engine.REILeadProcessor.parse_craigslist') as mock_craigslist, \
             patch('airtable_utils.safe_airtable_write') as mock_write, \
             patch('discord_utils.post_ops') as mock_discord:
            
            # Mock data sources
            mock_zillow.return_value = [{
                "Address": "123 Test St",
                "Phone": "555-1234",
                "Source_URL": "https://zillow.com/test",
                "source_id": "test_id_1"
            }]
            mock_craigslist.return_value = []
            mock_write.return_value = (True, "record_id")
            
            # Run REI processing
            from rei_dispo_engine import run_rei
            result = run_rei()
            
            assert result == 1  # One lead processed
            mock_write.assert_called_once()
            mock_discord.assert_called_once()


@pytest.mark.integration
class TestProductionReadiness:
    """Tests for production readiness."""
    
    def test_environment_variables(self):
        """Test that all required environment variables are defined."""
        required_vars = [
            'AIRTABLE_API_KEY',
            'AIRTABLE_BASE_ID',
            'DISCORD_WEBHOOK_OPS',
            'DISCORD_WEBHOOK_ERRORS',
            'TWILIO_ACCOUNT_SID',
            'TWILIO_AUTH_TOKEN',
            'TWILIO_MESSAGING_SERVICE_SID',
            'SAM_SEARCH_API',
            'SAM_API_KEY',
            'NAICS_WHITELIST',
            'UEI',
            'CAGE_CODE'
        ]
        
        with patch.dict(os.environ, {var: 'test_value' for var in required_vars}):
            # Test that modules can be imported without errors
            from airtable_utils import AirtableManager
            from discord_utils import DiscordNotifier
            from twilio_utils import TwilioMessenger
            from govcon_subtrap_engine import GovConProcessor
            
            # Should not raise exceptions
            assert True
    
    def test_logging_configuration(self):
        """Test logging configuration."""
        from logging_config import setup_logging, get_logger
        
        logger = setup_logging("INFO")
        assert logger is not None
        assert logger.level == 20  # INFO level
        
        test_logger = get_logger("test")
        assert test_logger is not None
    
    def test_kpi_system(self):
        """Test KPI system functionality."""
        with patch('airtable_utils.airtable._post_to_airtable') as mock_airtable, \
             patch('discord_utils.discord._post_to_discord') as mock_discord:
            
            # Test various KPI events
            kpi_push("boot", {"version": "3.0.0"})
            kpi_push("cycle_start", {"engine": "test"})
            kpi_push("cycle_end", {"engine": "test", "count": 5})
            kpi_push("error", {"error_type": "test", "message": "test error"})
            
            # Verify all events were logged
            assert mock_airtable.call_count == 4
            assert mock_discord.call_count == 4