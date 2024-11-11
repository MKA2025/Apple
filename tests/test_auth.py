"""
Test Suite for Gamdl Authentication Module

This module contains comprehensive tests for authentication mechanisms,
covering various scenarios and security aspects.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

# Import authentication modules
from gamdl.auth import (
    AuthManager,
    SpotifyAuthenticator,
    GoogleAuthenticator,
    AppleMusicAuthenticator
)

# Import exceptions
from gamdl.exceptions import (
    AuthenticationError,
    TokenExpiredError,
    InvalidCredentialsError
)

# Test utilities
from tests import generate_mock_data, load_test_config

class TestAuthentication:
    """
    Comprehensive test class for authentication functionality
    """

    @pytest.fixture
    def temp_config_dir(self):
        """
        Create a temporary configuration directory
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_credentials(self):
        """
        Generate mock credentials for testing
        """
        return {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'redirect_uri': 'https://localhost:8000/callback'
        }

    @pytest.mark.unit
    def test_auth_manager_initialization(self, temp_config_dir):
        """
        Test AuthManager initialization
        """
        auth_manager = AuthManager(config_dir=temp_config_dir)
        
        assert auth_manager is not None
        assert os.path.exists(temp_config_dir)
        assert hasattr(auth_manager, 'config_dir')
        assert hasattr(auth_manager, 'token_cache')

    @pytest.mark.unit
    def test_spotify_authenticator(self, mock_credentials):
        """
        Test Spotify authentication flow
        """
        spotify_auth = SpotifyAuthenticator(**mock_credentials)
        
        assert spotify_auth is not None
        assert spotify_auth.client_id == mock_credentials['client_id']
        assert spotify_auth.redirect_uri == mock_credentials['redirect_uri']

    @pytest.mark.integration
    def test_spotify_token_generation(self, mock_credentials):
        """
        Test Spotify token generation
        """
        spotify_auth = SpotifyAuthenticator(**mock_credentials)
        
        with patch.object(spotify_auth, '_request_access_token') as mock_token_request:
            # Mock successful token response
            mock_token_response = {
                'access_token': 'mock_access_token',
                'refresh_token': 'mock_refresh_token',
                'expires_in': 3600
            }
            mock_token_request.return_value = mock_token_response
            
            # Generate token
            token = spotify_auth.generate_token()
            
            assert token is not None
            assert 'access_token' in token
            assert 'refresh_token' in token

    @pytest.mark.unit
    def test_token_validation(self, mock_credentials):
        """
        Test token validation mechanisms
        """
        spotify_auth = SpotifyAuthenticator(**mock_credentials)
        
        # Valid token
        valid_token = {
            'access_token': 'valid_token',
            'expires_at': float('inf')  # Never expires
        }
        
        # Expired token
        expired_token = {
            'access_token': 'expired_token',
            'expires_at': 0  # Expired in the past
        }
        
        assert spotify_auth.is_token_valid(valid_token) is True
        assert spotify_auth.is_token_valid(expired_token) is False

    @pytest.mark.parametrize('service', [
        'spotify', 
        'google_music', 
        'apple_music'
    ])
    def test_multi_service_authentication(self, service, mock_credentials):
        """
        Test authentication for multiple music services
        """
        authenticator_map = {
            'spotify': SpotifyAuthenticator,
            'google_music': GoogleAuthenticator,
            'apple_music': AppleMusicAuthenticator
        }
        
        AuthClass = authenticator_map.get(service)
        auth_instance = AuthClass(**mock_credentials)
        
        assert auth_instance is not None
        assert hasattr(auth_instance, 'generate_token')
        assert hasattr(auth_instance, 'refresh_token')

    @pytest.mark.unit
    def test_authentication_error_handling(self, mock_credentials):
        """
        Test various authentication error scenarios
        """
        spotify_auth = SpotifyAuthenticator(**mock_credentials)
        
        # Test invalid credentials
        with pytest.raises(InvalidCredentialsError):
            spotify_auth.authenticate(
                username='invalid_user',
                password='wrong_password'
            )
        
        # Test token expiration
        with patch.object(spotify_auth, 'is_token_valid') as mock_validation:
            mock_validation.return_value = False
            
            with pytest.raises(TokenExpiredError):
                spotify_auth.validate_existing_token({})

    @pytest.mark.integration
    def test_token_refresh_mechanism(self, mock_credentials):
        """
        Test token refresh workflow
        """
        spotify_auth = SpotifyAuthenticator(**mock_credentials)
        
        # Mock existing token
        existing_token = {
            'access_token': 'old_token',
            'refresh_token': 'refresh_token_123',
            'expires_at': 0  # Expired token
        }
        
        with patch.object(spotify_auth, '_request_token_refresh') as mock_refresh:
            # Mock successful token refresh
            mock_refresh.return_value = {
                'access_token': 'new_access_token',
                'refresh_token': 'new_refresh_token',
                'expires_in': 3600
            }
            
            # Perform token refresh
            refreshed_token = spotify_auth.refresh_token(existing_token)
            
            assert refreshed_token is not None
            assert refreshed_token['access_token'] != existing_token['access_token']

    @pytest.mark.performance
    def test_authentication_performance(self, benchmark, mock_credentials):
        """
        Benchmark authentication performance
        """
        spotify_auth = SpotifyAuthenticator(**mock_credentials)
        
        def auth_benchmark():
            with patch.object(spotify_auth, '_request_access_token') as mock_token:
                mock_token.return_value = {
                    'access_token': 'perf_token',
                    'expires_in': 3600
                }
                return spotify_auth.generate_token()
        
        result = benchmark(auth_benchmark)
        assert result is not None

    def test_secure_credential_storage(self, temp_config_dir):
        """
        Test secure credential storage mechanism
        """
        auth_manager = AuthManager(config_dir=temp_config_dir)
        
        # Store credentials
        credentials = {
            'service': 'spotify',
            'client_id': 'test_client',
            'client_secret': 'test_secret'
        }
        
        # Store and retrieve credentials
        auth_manager.store_credentials(credentials)
        retrieved_creds = auth_manager.get_credentials('spotify')
        
        assert retrieved_creds is not None
        assert retrieved_creds['client_id'] == credentials['client_id']

def test_logging_configuration():
    """
    Test logging configuration for authentication
    """
    config = load_test_config()
    auth_manager = AuthManager(
        config_dir=tempfile.mkdtemp(),
        log_level=config.get('log_level', 'INFO')
    )
    
    assert hasattr(auth_manager, 'logger')
    assert auth_manager.logger is not None

# Error scenario tests
def test_missing_credentials():
    """
    Test authentication without credentials
    """
    with pytest.raises(AuthenticationError):
        SpotifyAuthenticator(
            client_id= None,
            client_secret=None,
            redirect_uri='https://localhost:8000/callback'
        )

def test_invalid_service_authentication():
    """
    Test authentication with an invalid service
    """
    with pytest.raises(ValueError):
        AuthManager(auth_service='invalid_service') ```python
"""
Test Suite for Gamdl Authentication Module

This module contains comprehensive tests for authentication mechanisms,
covering various scenarios and security aspects.
"""
