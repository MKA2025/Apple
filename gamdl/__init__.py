"""
GAMDL (Google Apple Music Downloader) Telegram Bot

This module provides a comprehensive solution for downloading 
Apple Music tracks via Telegram Bot.

Key Features:
- Apple Music API Integration
- Secure Music/Video Downloading
- Telegram Bot Interaction
- Advanced File Management
"""

import sys
import os
from pathlib import Path

# Ensure minimum Python version
if sys.version_info < (3, 8):
    raise RuntimeError("Python 3.8+ is required to run this application")

# Project Metadata
__title__ = "gamdl-telegram-bot"
__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"
__copyright__ = "Copyright 2024"

# Project Paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "configs"
DOWNLOAD_DIR = PROJECT_ROOT / "downloads"
LOGS_DIR = PROJECT_ROOT / "logs"
COMPLETED_DIR = PROJECT_ROOT / "completed"

# Ensure necessary directories exist
for directory in [CONFIG_DIR, DOWNLOAD_DIR, LOGS_DIR, COMPLETED_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Environment Configuration
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    print("python-dotenv not installed. Environment variables might not be loaded.")

# Logging Configuration
import logging
import logging.config
import yaml

def setup_logging(
    default_path=CONFIG_DIR / 'logging.yaml', 
    default_level=logging.INFO,
    env_key='LOG_CONFIG_PATH'
):
    """
    Setup logging configuration from yaml file
    
    Args:
        default_path (Path): Path to logging configuration yaml
        default_level (logging.Level): Default logging level
        env_key (str): Environment variable to override config path
    """
    path = os.getenv(env_key, default_path)
    
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        
        # Create logs directory if not exists
        log_dir = Path(config.get('handlers', {}).get('file', {}).get('filename', '.')).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Version Check and Compatibility
def version_check():
    """
    Check system compatibility and dependencies
    """
    try:
        import requests
        import aiogram
        import pywidevine
        
        logger.info(f"GAMDL Version: {__version__}")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Requests Version: {requests.__version__}")
        logger.info(f"Aiogram Version: {aiogram.__version__}")
        logger.info(f"Pywidevine Version: {pywidevine.__version__}")
    
    except ImportError as e:
        logger.error(f"Dependency missing: {e}")
        sys.exit(1)

# Runtime Checks
version_check()

# Public API
__all__ = [
    '__version__',
    'PROJECT_ROOT',
    'CONFIG_DIR',
    'DOWNLOAD_DIR',
    'LOGS_DIR',
    'COMPLETED_DIR',
    'setup_logging',
    'logger'
]
