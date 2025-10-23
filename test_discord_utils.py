import os
from unittest.mock import Mock, patch

import pytest
import requests

from discord_utils import _send_discord_message, post_error, post_kpi, post_ops


class TestDiscordUtils:
    """Test suite for discord_utils module."""

    @patch('discord_utils.requests.post')
    def test_send_discord_message_success(self, mock_post):
        """Test successful Discord message sending."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = _send_discord_message("https://discord.com/webhook", "Test message")

        assert result is True
        mock_post.assert_called_once()

        # Check payload structure
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['content'] == "Test message"
        assert payload['username'] == "KRIZZY-OPS"

    @patch('discord_utils.requests.post')
    def test_send_discord_message_http_error(self, mock_post):
        """Test Discord message sending with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_post.return_value = mock_response

        result = _send_discord_message("https://discord.com/webhook", "Test message")

        assert result is False

    @patch('discord_utils.requests.post')
    def test_send_discord_message_timeout(self, mock_post):
        """Test Discord message sending with timeout."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        result = _send_discord_message("https://discord.com/webhook", "Test message")

        assert result is False

    def test_send_discord_message_no_webhook(self):
        """Test Discord message sending with no webhook URL."""
        result = _send_discord_message("", "Test message")
        assert result is False

        result = _send_discord_message(None, "Test message")
        assert result is False

    @patch.dict(os.environ, {'DISCORD_WEBHOOK_OPS': 'https://discord.com/webhook/ops'})
    @patch('discord_utils._send_discord_message')
    def test_post_ops_success(self, mock_send):
        """Test successful ops message posting."""
        mock_send.return_value = True

        result = post_ops("Test ops message")

        assert result is True
        mock_send.assert_called_once()

        # Check that message is formatted correctly
        call_args = mock_send.call_args[0]
        assert "✅" in call_args[1]
        assert "Test ops message" in call_args[1]
        assert "[" in call_args[1]  # Timestamp formatting

    @patch.dict(os.environ, {'DISCORD_WEBHOOK_ERRORS': 'https://discord.com/webhook/errors'})
    @patch('discord_utils._send_discord_message')
    def test_post_error_success(self, mock_send):
        """Test successful error message posting."""
        mock_send.return_value = True

        result = post_error("Test error message")

        assert result is True
        mock_send.assert_called_once()

        # Check that message is formatted correctly
        call_args = mock_send.call_args[0]
        assert "❌" in call_args[1]
        assert "Test error message" in call_args[1]
        assert "[" in call_args[1]  # Timestamp formatting

    @patch.dict(os.environ, {'DISCORD_WEBHOOK_OPS': 'https://discord.com/webhook/ops'})
    @patch('discord_utils._send_discord_message')
    def test_post_kpi_success(self, mock_send):
        """Test successful KPI message posting."""
        mock_send.return_value = True

        result = post_kpi("test_event", {"count": 5, "status": "success"})

        assert result is True
        mock_send.assert_called_once()

        # Check that message is formatted correctly
        call_args = mock_send.call_args[0]
        assert "📊" in call_args[1]
        assert "test_event" in call_args[1]
        assert "count" in call_args[1]


class TestBackoffLogic:
    """Test backoff and retry logic for Discord messages."""

    @patch('discord_utils.requests.post')
    def test_backoff_on_server_error(self, mock_post):
        """Test that backoff works on server errors."""
        # First call fails with 500, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error"
        )
        mock_response_fail.status_code = 500

        mock_response_success = Mock()
        mock_response_success.raise_for_status.return_value = None

        mock_post.side_effect = [mock_response_fail, mock_response_success]

        result = _send_discord_message("https://discord.com/webhook", "Test message")

        # Should have been called twice due to retry
        assert mock_post.call_count == 2
        assert result is True

    @patch('discord_utils.requests.post')
    def test_backoff_gives_up_on_client_error(self, mock_post):
        """Test that backoff gives up on client errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "400 Bad Request"
        )
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        result = _send_discord_message("https://discord.com/webhook", "Test message")

        # Should only be called once (no retry on 4xx)
        assert mock_post.call_count == 1
        assert result is False

    @patch('discord_utils.requests.post')
    def test_backoff_on_rate_limit(self, mock_post):
        """Test backoff on rate limit (429)."""
        # First call fails with 429, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "429 Too Many Requests"
        )
        mock_response_fail.status_code = 429

        mock_response_success = Mock()
        mock_response_success.raise_for_status.return_value = None

        mock_post.side_effect = [mock_response_fail, mock_response_success]

        result = _send_discord_message("https://discord.com/webhook", "Test message")

        # Should retry on 429
        assert mock_post.call_count == 2
        assert result is True


class TestMessageFormatting:
    """Test message formatting and content."""

    @patch('discord_utils._send_discord_message')
    def test_ops_message_formatting(self, mock_send):
        """Test ops message formatting includes timestamp."""
        mock_send.return_value = True

        post_ops("Test message")

        call_args = mock_send.call_args[0]
        message = call_args[1]

        # Should include checkmark emoji
        assert "✅" in message
        # Should include timestamp in brackets
        assert "[" in message and "]" in message
        # Should include UTC
        assert "UTC" in message
        # Should include original message
        assert "Test message" in message

    @patch('discord_utils._send_discord_message')
    def test_error_message_formatting(self, mock_send):
        """Test error message formatting includes timestamp."""
        mock_send.return_value = True

        post_error("Test error")

        call_args = mock_send.call_args[0]
        message = call_args[1]

        # Should include X emoji
        assert "❌" in message
        # Should include timestamp in brackets
        assert "[" in message and "]" in message
        # Should include UTC
        assert "UTC" in message
        # Should include original message
        assert "Test error" in message

    @patch('discord_utils._send_discord_message')
    def test_kpi_message_formatting(self, mock_send):
        """Test KPI message formatting."""
        mock_send.return_value = True

        post_kpi("cycle_complete", {"count": 10, "duration": 5.5})

        call_args = mock_send.call_args[0]
        message = call_args[1]

        # Should include chart emoji
        assert "📊" in message
        # Should include KPI label
        assert "KPI:" in message
        # Should include event name
        assert "cycle_complete" in message
        # Should include data
        assert "count" in message


if __name__ == "__main__":
    pytest.main([__file__])
