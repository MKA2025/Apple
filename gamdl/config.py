"""
Configuration Management Module

This module provides robust configuration management with support for:
- Environment variable loading
- YAML configuration
- Validation
- Secure credential handling
"""

import os
import sys
from typing import Any, Dict, Optional
from pathlib import Path

import yaml
from dotenv import load_dotenv
import jsonschema
from cryptography.fernet import Fernet

# Local imports
from gamdl import PROJECT_ROOT, logger

# Load environment variables
load_dotenv(PROJECT_ROOT / '.env')

class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass

class ConfigManager:
    """
    Comprehensive Configuration Management Class
    
    Handles loading, validation, and secure management of configurations
    """
    
    # Configuration schema for validation
    _CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "telegram": {
                "type": "object",
                "properties": {
                    "bot_token": {"type": "string"},
                    "admin_users": {
                        "type": "array",
                        "items": {"type": "number"}
                    }
                },
                "required": ["bot_token"]
            },
            "apple_music": {
                "type": "object",
                "properties": {
                    "cookies_path": {"type": "string"},
                    "language": {"type": "string"},
                    "storefront": {"type": "string"}
                }
            },
            "download": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string"},
                    "max_download_size": {"type": "number"},
                    "allowed_formats": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "security": {
                "type": "object",
                "properties": {
                    "rate_limit": {"type": "number"},
                    "download_timeout": {"type": "number"}
                }
            }
        }
    }

    def __init__(
        self, 
        config_path: Optional[Path] = None, 
        env_prefix: str = 'GAMDL_'
    ):
        """
        Initialize ConfigManager
        
        Args:
            config_path (Path, optional): Custom configuration file path
            env_prefix (str, optional): Prefix for environment variables
        """
        self.env_prefix = env_prefix
        self.config_path = config_path or PROJECT_ROOT / 'configs' / 'config.yaml'
        self._encryption_key = self._load_or_generate_encryption_key()
        self.config = self._load_configuration()

    def _load_or_generate_encryption_key(self) -> bytes:
        """
        Load or generate an encryption key for sensitive configurations
        
        Returns:
            bytes: Encryption key
        """
        key_path = PROJECT_ROOT / '.encryption_key'
        
        if key_path.exists():
            return key_path.read_bytes()
        
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        key_path.chmod(0o600)  # Restrict permissions
        
        return key

    def _load_configuration(self) -> Dict[str, Any]:
        """
        Load and validate configuration
        
        Returns:
            Dict: Validated configuration
        """
        try:
            # Load base configuration
            config = self._load_yaml_config()
            
            # Override with environment variables
            config = self._override_with_env_vars(config)
            
            # Validate configuration
            self._validate_config(config)
            
            return config
        
        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def _load_yaml_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file
        
        Returns:
            Dict: Configuration dictionary
        """
        default_config = {
            "telegram": {
                "bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
                "admin_users": [int(uid) for uid in os.getenv("ADMIN_USER_IDS", "").split(",") if uid]
            },
            "apple_music": {
                "cookies_path": os.getenv("APPLE_MUSIC_COOKIES_PATH", "./cookies/cookies.txt"),
                "language": os.getenv("APPLE_MUSIC_LANGUAGE", "en"),
                "storefront": os.getenv("APPLE_MUSIC_STOREFRONT", "us")
            },
            "download": {
                "output_path": os.getenv("DOWNLOAD_OUTPUT_PATH", "./downloads"),
                "max_download_size": int(os.getenv("MAX_DOWNLOAD_SIZE_GB", 10)),
                "allowed_formats": ["m4a", "mp4"]
            },
            "security": {
                "rate_limit": int(os.getenv("RATE_LIMIT_DOWNLOADS", 3)),
                "download_timeout": int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", 600))
            }
        }
        
        if not self.config_path.exists():
            logger.warning(f"Config file not found at {self.config_path}. Using default configuration.")
            return default_config
        
        with open(self.config_path, 'r') as f:
            file_config = yaml.safe_load(f) or {}
        
        # Merge default and file configurations
        merged_config = {**default_config, **file_config}
        return merged_config

    def _override_with_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override configuration with environment variables
        
        Args:
            config (Dict): Original configuration
        
        Returns:
            Dict: Updated configuration
        """
        for section, section_config in config.items():
            if isinstance(section_config, dict):
                for key, value in section_config.items():
                    env_key = f"{self.env_prefix}{section.upper()}_{key.upper()}"
                    env_value = os.getenv(env_key)
                    
                    if env_value is not None:
                        # Type conversion
                        if isinstance(value, int):
                            config[section][key] = int(env_value)
                        elif isinstance(value, list):
                            config[section][key] = env_value.split(',')
                        else:
                            config[section][key] = env_value
        
        return config

    def _validate_config(self, config: Dict[str, Any]):
        """
        Validate configuration against schema
        
        Args:
            config (Dict): Configuration to validate
        
        Raises:
            jsonschema.ValidationError: If configuration is invalid
        """
        try:
            jsonschema.validate(instance=config, schema=self._CONFIG_SCHEMA)
        except jsonschema.ValidationError as e:
            raise ConfigurationError(f"Invalid configuration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve configuration value
        
        Args:
            key (str): Dot-separated configuration key
            default (Any, optional): Default value if key not found
        
        Returns:
            Any: Configuration value
        """
        try:
            value = self.config
            for k in key.split('.'):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def encrypt_sensitive_data(self, data: str) -> str:
        """
        Encrypt sensitive configuration data
        
        Args:
            data (str): Data to encrypt
        
        Returns:
            str: Encrypted data
        """
        f = Fernet(self._encryption_key)
        return f.encrypt(data.encode()).decode()

        def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive configuration data
        
        Args:
            encrypted_data (str): Encrypted data to decrypt
        
        Returns:
            str: Decrypted data
        
        Raises:
            ConfigurationError: If decryption fails
        """
        try:
            f = Fernet(self._encryption_key)
            return f.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ConfigurationError("Failed to decrypt sensitive data")

    def save_config(self, config: Dict[str, Any] = None):
        """
        Save current or provided configuration to YAML file
        
        Args:
            config (Dict, optional): Configuration to save. 
                                     If None, saves current configuration
        """
        if config is None:
            config = self.config
        
        # Validate new configuration before saving
        self._validate_config(config)
        
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write configuration
        with open(self.config_path, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        
        logger.info(f"Configuration saved to {self.config_path}")

    def interactive_config_setup(self):
        """
        Interactive configuration setup wizard
        """
        import click
        
        click.echo("🔧 GAMDL Configuration Wizard")
        
        # Telegram Configuration
        click.echo("\n🤖 Telegram Bot Configuration")
        bot_token = click.prompt("Enter Telegram Bot Token", type=str)
        admin_users_input = click.prompt(
            "Enter Admin User IDs (comma-separated)", 
            type=str, 
            default=""
        )
        admin_users = [int(uid.strip()) for uid in admin_users_input.split(',') if uid.strip()]
        
        # Apple Music Configuration
        click.echo("\n🎵 Apple Music Configuration")
        cookies_path = click.prompt(
            "Path to Apple Music Cookies", 
            type=click.Path(exists=True),
            default="./cookies/cookies.txt"
        )
        language = click.prompt("Apple Music Language Code", type=str, default="en")
        storefront = click.prompt("Apple Music Storefront", type=str, default="us")
        
        # Download Configuration
        click.echo("\n⬇️ Download Configuration")
        output_path = click.prompt(
            "Download Output Path", 
            type=click.Path(file_okay=False, dir_okay=True),
            default="./downloads"
        )
        max_download_size = click.prompt(
            "Max Download Size (GB)", 
            type=int, 
            default=10
        )
        
        # Security Configuration
        click.echo("\n🛡️ Security Configuration")
        rate_limit = click.prompt("Downloads per User", type=int, default=3)
        download_timeout = click.prompt("Download Timeout (seconds)", type=int, default=600)
        
        # Construct new configuration
        new_config = {
            "telegram": {
                "bot_token": bot_token,
                "admin_users": admin_users
            },
            "apple_music": {
                "cookies_path": str(cookies_path),
                "language": language,
                "storefront": storefront
            },
            "download": {
                "output_path": str(output_path),
                "max_download_size": max_download_size,
                "allowed_formats": ["m4a", "mp4"]
            },
            "security": {
                "rate_limit": rate_limit,
                "download_timeout": download_timeout
            }
        }
        
        # Save configuration
        self.save_config(new_config)
        click.echo("\n✅ Configuration saved successfully!")

# Create a singleton configuration manager
config = ConfigManager()

# Expose configuration getter as a module-level function
def get_config(key: str, default: Any = None) -> Any:
    """
    Global configuration getter
    
    Args:
        key (str): Dot-separated configuration key
        default (Any, optional): Default value
    
    Returns:
        Any: Configuration value
    """
    return config.get(key, default)

# Export key objects
__all__ = [
    'ConfigManager', 
    'config', 
    'get_config', 
    'ConfigurationError'
]
