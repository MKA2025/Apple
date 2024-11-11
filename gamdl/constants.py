"""
Constants and Configurations for GAMDL

This module defines global constants, configuration parameters, 
and utility constants used across the application.
"""

from enum import Enum, auto
from pathlib import Path
import os

# Project Root and Directory Configurations
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / 'configs'
DOWNLOAD_DIR = PROJECT_ROOT / 'downloads'
TEMP_DIR = PROJECT_ROOT / 'temp'
LOGS_DIR = PROJECT_ROOT / 'logs'

# Create necessary directories if they don't exist
for directory in [CONFIG_DIR, DOWNLOAD_DIR, TEMP_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Application Metadata
class AppMetadata:
    NAME = "GAMDL"
    VERSION = "1.0.0"
    DESCRIPTION = "Apple Music Downloader and Telegram Bot"
    AUTHOR = "Your Name"
    GITHUB_REPO = "https://github.com/yourusername/gamdl"

# Logging Configurations
class LoggingConfig:
    DEFAULT_LEVEL = "INFO"
    MAX_LOG_FILES = 5
    MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Download Related Enums and Constants
class DownloadStatus(Enum):
    PENDING = auto()
    DOWNLOADING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

class MediaType(Enum):
    SONG = "song"
    ALBUM = "album"
    PLAYLIST = "playlist"
    MUSIC_VIDEO = "music_video"
    POST = "post"

# Apple Music Related Constants
class AppleMusicConstants:
    STOREFRONT_DEFAULT = "us"
    LANGUAGE_DEFAULT = "en-US"
    COVER_SIZE_DEFAULT = 1200
    
    CODEC_PREFERENCES = {
        "song": [
            "aac",
            "aac-he",
            "aac-binaural",
            "alac"
        ],
        "music_video": [
            "h264",
            "h265"
        ]
    }

# Telegram Bot Constants
class TelegramBotConstants:
    MAX_MESSAGE_LENGTH = 4096
    CALLBACK_QUERY_TIMEOUT = 30
    DEFAULT_RATE_LIMIT = 3  # Downloads per user
    ADMIN_COMMANDS = [
        'start', 
        'help', 
        'status', 
        'config', 
        'stats'
    ]

# File and Path Related Constants
class FileConstants:
    ALLOWED_EXTENSIONS = [
        '.m4a',   # Audio
        '.mp4',   # Music Videos
        '.m4v',   # Video
        '.flac',  # Lossless Audio
        '.mkv'    # Multiplex Video
    ]
    
    MAX_FILENAME_LENGTH = 255
    ILLEGAL_CHARS = r'[\\/:*?"<>|]'
    REPLACEMENT_CHAR = '_'

# Security and Rate Limiting
class SecurityConstants:
    DOWNLOAD_TIMEOUT = 600  # 10 minutes
    MAX_CONCURRENT_DOWNLOADS = 5
    RATE_LIMIT_WINDOW = 60  # seconds

# Error and Exception Constants
class ErrorMessages:
    DOWNLOAD_FAILED = "Download failed: {reason}"
    INVALID_URL = "Invalid Apple Music URL"
    UNAUTHORIZED = "Unauthorized access"
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Please try again later."

# Supported Platforms
class SupportedPlatforms(Enum):
    APPLE_MUSIC = "apple_music"
    ITUNES = "itunes"

# Utility Functions
def sanitize_filename(filename: str) -> str:
    """
    Sanitize filenames by removing illegal characters
    
    Args:
        filename (str): Original filename
    
    Returns:
        str: Sanitized filename
    """
    import re
    
    # Remove or replace illegal characters
    sanitized = re.sub(
        FileConstants.ILLEGAL_CHARS, 
        FileConstants.REPLACEMENT_CHAR, 
        filename
    )
    
    # Truncate filename if too long
    return sanitized[:FileConstants.MAX_FILENAME_LENGTH]

# Export key constants and utilities
__all__ = [
    'PROJECT_ROOT',
    'CONFIG_DIR',
    'DOWNLOAD_DIR',
    'TEMP_DIR',
    'LOGS_DIR',
    'AppMetadata',
    'LoggingConfig',
    'DownloadStatus',
    'MediaType',
    'AppleMusicConstants',
    'TelegramBotConstants',
    'FileConstants',
    'SecurityConstants',
    'ErrorMessages',
    'SupportedPlatforms',
    'sanitize_filename'
]
