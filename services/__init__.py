"""
Services Module Initialization

This module provides a centralized management and initialization
for various services used across the application.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from gamdl.apis import (
    AppleMusicAPI,
    iTunesAPI,
    TelegramAPI,
    SpotifyAPI,
    GoogleDriveAPI
)
from gamdl.models import (
    ServiceCredentials,
    ServiceConfiguration
)
from gamdl.config import ConfigManager
from gamdl.utils import SingletonMeta

logger = logging.getLogger(__name__)

class ServiceManager(metaclass=SingletonMeta):
    """
    Centralized service management and initialization
    """

    def __init__(
        self, 
        config_manager: Optional[ConfigManager] = None
    ):
        """
        Initialize service manager

        Args:
            config_manager (Optional[ConfigManager]): Configuration manager
        """
        self.config_manager = config_manager or ConfigManager()
        self._services: Dict[str, Any] = {}
        self._initialize_services()

    def _initialize_services(self):
        """
        Initialize all configured services
        """
        service_configs = self.config_manager.get_service_configurations()
        
        for service_name, config in service_configs.items():
            try:
                self._initialize_service(service_name, config)
            except Exception as e:
                logger.error(f"Failed to initialize {service_name} service: {e}")

    def _initialize_service(
        self, 
        service_name: str, 
        config: ServiceConfiguration
    ):
        """
        Initialize a specific service

        Args:
            service_name (str): Name of the service
            config (ServiceConfiguration): Service configuration
        """
        credentials = ServiceCredentials(
            token=config.token,
            client_id=config.client_id,
            client_secret=config.client_secret
        )

        service_map = {
            'apple_music': AppleMusicAPI,
            'itunes': iTunesAPI,
            'telegram': TelegramAPI,
            'spotify': SpotifyAPI,
            'google_drive': GoogleDriveAPI
        }

        service_class = service_map.get(service_name)
        if service_class:
            self._services[service_name] = service_class(
                credentials,
                **config.extra_params
            )

    def get_service(
        self, 
        service_name: str
    ) -> Optional[Any]:
        """
        Retrieve a specific initialized service

        Args:
            service_name (str): Name of the service

        Returns:
            Optional[Any]: Initialized service instance
        """
        return self._services.get(service_name)

    def register_service(
        self, 
        service_name: str, 
        service_instance: Any
    ):
        """
        Manually register a service instance

        Args:
            service_name (str): Name of the service
            service_instance (Any): Service instance to register
        """
        self._services[service_name] = service_instance

    def get_all_services(self) -> Dict[str, Any]:
        """
        Get all initialized services

        Returns:
            Dict[str, Any]: Dictionary of service instances
        """
        return self._services.copy()

    def validate_services(self) -> Dict[str, bool]:
        """
        Validate all initialized services

        Returns:
            Dict[str, bool]: Service validation status
        """
        service_status = {}
        
        for name, service in self._services.items():
            try:
                service_status[name] = service.validate_connection()
            except Exception:
                service_status[name] = False
        
        return service_status

# Convenience function for quick service access
def get_service(service_name: str) -> Optional[Any]:
    """
    Quick access to service instances

    Args:
        service_name (str): Name of the service

    Returns:
        Optional[Any]: Initialized service instance
    """
    return ServiceManager().get_service(service_name)

# Public API
__all__ = [
    'ServiceManager', 
    'get_service'
]
