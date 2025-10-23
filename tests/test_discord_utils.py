"""Tests for discord_utils module"""

import pytest
from unittest.mock import Mock, patch
import requests
from discord_utils import post_ops, post_error, post_err


class TestDiscordUtils:
    """Test cases for Discord utilities"""
    
    @patch('discord_utils.OPS_WEBHOOK', 'https://discord.com/api/webhooks/test')
    @patch('discord_utils.requests.post')
    def test_post_ops_success(self, mock_post):
        """Test successful Discord ops post"""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # Test
        result = post_ops("Test message")
        
        # Assertions
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "✅ Test message" in call_args[1]["json"]["content"]
    
    @patch('discord_utils.OPS_WEBHOOK', 'https://discord.com/api/webhooks/test')
    @patch('discord_utils.requests.post')
    def test_post_ops_http_error(self, mock_post):
        """Test Discord ops post with HTTP error"""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        mock_post.side_effect = requests.exceptions.HTTPError("Bad Request")
        
        # Test
        with pytest.raises(Exception):  # Should raise due to retry logic
            post_ops("Test message")
    
    @patch('discord_utils.OPS_WEBHOOK', 'https://discord.com/api/webhooks/test')
    @patch('discord_utils.requests.post')
    def test_post_ops_rate_limit(self, mock_post):
        """Test Discord ops post with rate limiting"""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        mock_post.side_effect = requests.exceptions.HTTPError("Rate Limited")
        
        # Test
        with pytest.raises(Exception):  # Should raise due to retry logic
            post_ops("Test message")
    
    @patch('discord_utils.OPS_WEBHOOK', None)
    def test_post_ops_no_webhook(self):
        """Test Discord ops post with no webhook configured"""
        # Test
        result = post_ops("Test message")
        
        # Assertions
        assert result is False
    
    @patch('discord_utils.ERROR_WEBHOOK', 'https://discord.com/api/webhooks/test')
    @patch('discord_utils.requests.post')
    def test_post_error_success(self, mock_post):
        """Test successful Discord error post"""
        # Setup
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Test
        result = post_error("Test error")
        
        # Assertions
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "❌ Test error" in call_args[1]["json"]["content"]
    
    @patch('discord_utils.ERROR_WEBHOOK', None)
    def test_post_error_no_webhook(self):
        """Test Discord error post with no webhook configured"""
        # Test
        result = post_error("Test error")
        
        # Assertions
        assert result is False
    
    def test_post_err_alias(self):
        """Test post_err is alias for post_error"""
        # Test
        assert post_err is post_error