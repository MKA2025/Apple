"""
Authentication Service Module

Provides centralized authentication management, token handling,
and secure credential storage across different services.
"""

from __future__ import annotations

import os
import time
import base64
import hashlib
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta

import jwt
import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from gamdl.models import (
    AuthCredential,
    AuthToken,
    ServiceCredentials
)
from gamdl.config import ConfigManager
from gamdl.utils import SingletonMeta

logger = logging.getLogger(__name__)

class AuthService(metaclass=SingletonMeta):
    """
    Centralized authentication and credential management service
    """

    def __init__(
        self, 
        config_manager: Optional[ConfigManager] = None,
        secret_key: Optional[str] = None
    ):
        """
        Initialize authentication service

        Args:
            config_manager (Optional[ConfigManager]): Configuration manager
            secret_key (Optional[str]): Master encryption key
        """
        self.config_manager = config_manager or ConfigManager()
        self._secret_key = secret_key or self._generate_secret_key()
        self._encryption_key = self._derive_encryption_key()
        self._credentials_store: Dict[str, AuthCredential] = {}
        self._token_cache: Dict[str, AuthToken] = {}
        
        self._load_stored_credentials()

    def _generate_secret_key(self) -> str:
        """
        Generate a secure random secret key

        Returns:
            str: Generated secret key
        """
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    def _derive_encryption_key(self) -> bytes:
        """
        Derive a secure encryption key from the secret key

        Returns:
            bytes: Derived encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'gamdl_auth_salt',
            iterations=100000
        )
        return base64.urlsafe_b64encode(
            kdf.derive(self._secret_key.encode())
        )

    def _load_stored_credentials(self):
        """
        Load stored credentials from configuration
        """
        try:
            stored_credentials = self.config_manager.get_auth_credentials()
            for service, cred in stored_credentials.items():
                self.store_credentials(service, cred)
        except Exception as e:
            logger.error(f"Error loading stored credentials: {e}")

    def store_credentials(
        self, 
        service: str, 
        credentials: Union[ServiceCredentials, Dict[str, Any]]
    ) -> AuthCredential:
        """
        Securely store service credentials

        Args:
            service (str): Service name
            credentials (Union[ServiceCredentials, Dict[str, Any]]): Credentials to store

        Returns:
            AuthCredential: Stored credential object
        """
        try:
            if isinstance(credentials, dict):
                credentials = ServiceCredentials(**credentials)

            encrypted_token = self._encrypt_credential(credentials.token)
            encrypted_client_id = self._encrypt_credential(credentials.client_id)
            encrypted_client_secret = self._encrypt_credential(credentials.client_secret)

            auth_credential = AuthCredential(
                service=service,
                token=encrypted_token,
                client_id=encrypted_client_id,
                client_secret=encrypted_client_secret
            )

            self._credentials_store[service] = auth_credential
            self.config_manager.update_auth_credentials(
                service, 
                auth_credential.to_dict()
            )

            return auth_credential

        except Exception as e:
            logger.error(f"Credential storage error for {service}: {e}")
            raise

    def get_credentials(self, service: str) -> Optional[ServiceCredentials]:
        """
        Retrieve decrypted credentials for a service

        Args:
            service (str): Service name

        Returns:
            Optional[ServiceCredentials]: Decrypted credentials
        """
        try:
            credential = self._credentials_store.get(service)
            if not credential:
                return None

            return ServiceCredentials(
                token=self._decrypt_credential(credential.token),
                client_id=self._decrypt_credential(credential.client_id),
                client_secret=self._decrypt_credential(credential.client_secret)
            )

        except Exception as e:
            logger.error(f"Credential retrieval error for {service}: {e}")
            return None

    def _encrypt_credential(self, credential: Optional[str]) -> Optional[str]:
        """
        Encrypt a credential using Fernet symmetric encryption

        Args:
            credential (Optional[str]): Credential to encrypt

        Returns:
            Optional[str]: Encrypted credential
        """
        if not credential:
            return None

        f = Fernet(self._encryption_key)
        return f.encrypt(credential.encode()).decode()

    def _decrypt_credential(self, encrypted_credential: Optional[str]) -> Optional[str]:
        """
        Decrypt a credential using Fernet symmetric encryption

        Args:
            encrypted_credential (Optional[str]): Encrypted credential

        Returns:
            Optional[str]: Decrypted credential
        """
        if not encrypted_credential:
            return None

        f = Fernet(self._encryption_key)
        return f.decrypt(encrypted_credential.encode()).decode()

    def generate_jwt_token(
        self, 
        payload: Dict[str, Any], 
        expiration: int = 3600
    ) -> str:
        """
        Generate a JWT token

        Args:
            payload (Dict[str, Any]): Token payload
            expiration (int): Token expiration time in seconds

        Returns:
            str: Generated JWT token
        """
        try:
            payload['exp'] = datetime.utcnow() + timedelta(seconds=expiration)
            payload['iat'] = datetime.utcnow()
            
            return jwt.encode(
                payload, 
                self._secret_key, 
                algorithm='HS256'
            )
        except Exception as e:
            logger.error(f"JWT token generation error: {e}")
            raise

    def validate_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a JWT token

        Args:
            token (str): JWT token to validate

        Returns:
            Optional[Dict[str, Any]]: Decoded token payload
        """
        try:
            return jwt.decode(
                token, 
                self._secret_key, 
                algorithms=['HS256']
            )
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
        
        return None

    def cache_access_token(
        self, 
        service: str, 
        token: str, 
        expiration: Optional[int] = None
    ) -> AuthToken:
        """
        Cache an access token for a service

        Args:
            service (str): Service name
            token (str): Access token
            expiration (Optional[int]): Token expiration time

        Returns:
            AuthToken: Cached token object
        """
        auth_token = AuthToken(
            service=service,
            token=token,
            expires_at=time.time() + (expiration or 3600)
        )

        self._token_cache[service] = auth_token
        return auth_token

    def get_cached_token(self, service: str) -> Optional[str]:
        """
        Retrieve a cached access token

        Args:
            service (str): Service name

        Returns:
            Optional[str]: Cached access token
        """
        token = self._token_cache.get(service) if token and token.expires_at > time.time():
            return token.token
        return None

    def clear_cached_token(self, service: str):
        """
        Clear the cached access token for a service

        Args:
            service (str): Service name
        """
        if service in self._token_cache:
            del self._token_cache[service]

# Public API
__all__ = [
    'AuthService'
]
