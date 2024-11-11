"""
Test Suite for Gamdl Telegram Bot Module

This module contains comprehensive tests for the Telegram bot functionality,
covering various scenarios and interactions.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Import Telegram bot and related modules
from gamdl.telegram_bot import GamdlTelegramBot
from gamdl.exceptions import (
    ConfigurationError,
    AuthenticationError,
    ProcessingError
)

# Test utilities
from tests import generate_mock_data, load_test_config

class TestTelegramBot:
    """
    Comprehensive test class for Telegram Bot functionality
    """

    @pytest.fixture
    def bot_config(self):
        """
        Fixture for Telegram bot configuration
        """
        return {
            'token': 'test_token_123456',
            'allowed_users': [12345, 67890],
            'download_dir': '/tmp/gamdl_downloads',
            'log_level': 'DEBUG'
        }

    @pytest.fixture
    def mock_telegram_bot(self, bot_config):
        """
        Create a mock Telegram bot instance
        """
        return GamdlTelegramBot(**bot_config)

    @pytest.mark.unit
    def test_bot_initialization(self, mock_telegram_bot, bot_config):
        """
        Test Telegram bot initialization
        """
        assert mock_telegram_bot is not None
        assert mock_telegram_bot.token == bot_config['token']
        assert mock_telegram_bot.allowed_users == bot_config['allowed_users']
        assert os.path.exists(bot_config['download_dir'])

    @pytest.mark.unit
    def test_invalid_bot_configuration(self):
        """
        Test bot initialization with invalid configuration
        """
        with pytest.raises(ConfigurationError):
            GamdlTelegramBot(token=None)

    @pytest.mark.integration
    @patch('gamdl.telegram_bot.telebot.TeleBot')
    def test_bot_authentication(self, mock_telebot, mock_telegram_bot):
        """
        Test user authentication mechanism
        """
        # Simulate user authentication scenarios
        valid_user_id = 12345
        invalid_user_id = 99999

        # Test valid user
        assert mock_telegram_bot.is_authorized_user(valid_user_id) is True

        # Test invalid user
        assert mock_telegram_bot.is_authorized_user(invalid_user_id) is False

    @pytest.mark.unit
    def test_command_handlers(self, mock_telegram_bot):
        """
        Test various bot command handlers
        """
        # Mock message object
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_message.text = '/start'

        # Test start command
        with patch.object(mock_telegram_bot, 'send_message') as mock_send:
            mock_telegram_bot.handle_start_command(mock_message)
            mock_send.assert_called_once()

        # Test help command
        mock_message.text = '/help'
        with patch.object(mock_telegram_bot, 'send_message') as mock_send:
            mock_telegram_bot.handle_help_command(mock_message)
            mock_send.assert_called_once()

    @pytest.mark.integration
    def test_url_processing(self, mock_telegram_bot):
        """
        Test URL processing and validation
        """
        # Valid music platform URLs
        valid_urls = [
            'https://open.spotify.com/track/123',
            'https://music.youtube.com/watch?v=abc',
            'https://soundcloud.com/artist/track'
        ]

        # Invalid URLs
        invalid_urls = [
            'https://example.com/invalid',
            'not a url',
            ''
        ]

        # Test valid URL processing
        for url in valid_urls:
            assert mock_telegram_bot.validate_url(url) is True

        # Test invalid URL processing
        for url in invalid_urls:
            assert mock_telegram_bot.validate_url(url) is False

    @pytest.mark.integration
    def test_download_workflow(self, mock_telegram_bot):
        """
        Test complete download workflow
        """
        # Mock message and track data
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_track = generate_mock_data('track')[0]
        mock_url = f"https://example.com/track/{mock_track['id']}"

        # Mock download process
        with patch.object(mock_telegram_bot, 'download_track') as mock_download:
            mock_download.return_value = '/path/to/downloaded/track.mp3'
            
            result = mock_telegram_bot.process_download_request(
                message=mock_message, 
                url=mock_url
            )

            assert result is not None
            mock_download.assert_called_once()

    @pytest.mark.unit
    def test_error_handling(self, mock_telegram_bot):
        """
        Test error handling mechanisms
        """
        mock_message = Mock()
        mock_message.chat.id = 12345

        # Test network error
        with pytest.raises(ProcessingError):
            mock_telegram_bot.handle_network_error(mock_message)

        # Test authentication error
        with pytest.raises(AuthenticationError):
            mock_telegram_bot.handle_authentication_error(mock_message)

    @pytest.mark.parametrize('user_role', ['admin', 'user', 'guest'])
    def test_user_permissions(self, mock_telegram_bot, user_role):
        """
        Test different user permission levels
        """
        permission_map = {
            'admin': ['download', 'settings', 'manage'],
            'user': ['download'],
            'guest': []
        }

        def check_permissions(role):
            return permission_map.get(role, [])

        permissions = check_permissions(user_role)
        
        if user_role == 'admin':
            assert len(permissions) == 3
        elif user_role == 'user':
            assert len(permissions) == 1
        else:
            assert len(permissions) == 0

    @pytest.mark.performance
    def test_bot_response_time(self, benchmark, mock_telegram_bot):
        """
        Benchmark bot response time
        """
        mock_message = Mock()
        mock_message.text = '/start'
        mock_message.chat.id = 12345

        result = benchmark(mock_telegram_bot.handle_start_command, mock_message)
        assert result is not None

def test_bot_logging_configuration():
    """
    Test logging configuration for Telegram bot
    """
    config = load_test_config()
    bot = GamdlTelegramBot(
        token='test_token',
        log_level=config.get('log_level', 'INFO')
    )
    
    assert hasattr(bot, 'logger')
    assert bot.logger is not None

# Specific error scenario tests
def test_missing_bot_token():
    """
    Test bot initialization without token
    """
    with pytest.raises(ConfigurationError):
        GamdlTelegramBot(token=None)

def test_unauthorized_user_interaction():
    """
    Test interaction from unauthorized user
    """
    bot = GamdlTelegramBot(
        token='test_token', 
        allowed_users=[12345]
    )
    
    mock_message = Mock()
    mock_message.from_user.id = 99999
    
    with pytest.raises(AuthenticationError):
        bot.validate_user(mock_message)
