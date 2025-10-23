"""Tests for twilio_utils module"""

import pytest
from unittest.mock import Mock, patch
from twilio.base.exceptions import TwilioException
from twilio_utils import send_msg, send_sms, send_bulk_sms, _get_client


class TestTwilioUtils:
    """Test cases for Twilio utilities"""
    
    @patch('twilio_utils.TWILIO_MESSAGING_SERVICE_SID', 'test_service_sid')
    @patch('twilio_utils.Client')
    def test_send_msg_success(self, mock_client_class):
        """Test successful SMS send"""
        # Setup
        mock_client = Mock()
        mock_message = Mock()
        mock_message.sid = "test_sid"
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value = mock_client
        
        # Test
        result = send_msg("+1234567890", "Test message")
        
        # Assertions
        assert result is True
        mock_client.messages.create.assert_called_once_with(
            messaging_service_sid='test_service_sid',
            body="Test message",
            to="+1234567890"
        )
    
    @patch('twilio_utils.TWILIO_MESSAGING_SERVICE_SID', 'test_service_sid')
    @patch('twilio_utils.Client')
    def test_send_msg_content_filtered(self, mock_client_class):
        """Test SMS send with content filtering (30007 error)"""
        # Setup
        mock_client = Mock()
        error = TwilioException("Content filtered")
        error.code = 30007
        mock_client.messages.create.side_effect = error
        mock_client_class.return_value = mock_client
        
        # Test
        result = send_msg("+1234567890", "Test message", content_rotation=True)
        
        # Assertions
        assert result is True  # Should succeed with rotation
        assert mock_client.messages.create.call_count == 2  # Original + rotation
    
    @patch('twilio_utils.TWILIO_MESSAGING_SERVICE_SID', 'test_service_sid')
    @patch('twilio_utils.Client')
    def test_send_msg_rate_limited(self, mock_client_class):
        """Test SMS send with rate limiting"""
        # Setup
        mock_client = Mock()
        error = TwilioException("Rate limited")
        error.code = 429
        mock_client.messages.create.side_effect = error
        mock_client_class.return_value = mock_client
        
        # Test
        with pytest.raises(TwilioException):  # Should raise due to retry logic
            send_msg("+1234567890", "Test message")
    
    @patch('twilio_utils.TWILIO_MESSAGING_SERVICE_SID', None)
    def test_send_msg_no_service_sid(self):
        """Test SMS send with no messaging service SID"""
        # Test
        result = send_msg("+1234567890", "Test message")
        
        # Assertions
        assert result is False
    
    def test_send_sms_alias(self):
        """Test send_sms is alias for send_msg"""
        # Test
        assert send_sms is send_msg
    
    @patch('twilio_utils.send_msg')
    def test_send_bulk_sms(self, mock_send_msg):
        """Test bulk SMS sending"""
        # Setup
        mock_send_msg.side_effect = [True, False, True]
        
        # Test
        recipients = ["+1111111111", "+2222222222", "+3333333333"]
        results = send_bulk_sms(recipients, "Test message")
        
        # Assertions
        assert results == {
            "+1111111111": True,
            "+2222222222": False,
            "+3333333333": True
        }
        assert mock_send_msg.call_count == 3
    
    @patch('twilio_utils.TWILIO_ACCOUNT_SID', 'test_sid')
    @patch('twilio_utils.TWILIO_AUTH_TOKEN', 'test_token')
    @patch('twilio_utils.Client')
    def test_get_client_success(self, mock_client_class):
        """Test client creation with valid credentials"""
        # Setup
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Test
        client = _get_client()
        
        # Assertions
        assert client == mock_client
        mock_client_class.assert_called_once_with('test_sid', 'test_token')
    
    @patch('twilio_utils.TWILIO_ACCOUNT_SID', None)
    def test_get_client_missing_credentials(self):
        """Test client creation with missing credentials"""
        # Test
        with pytest.raises(Exception):  # Should raise TwilioError
            _get_client()