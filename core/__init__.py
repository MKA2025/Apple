"""
GAMDL Core Initialization Module

This module serves as the entry point and initialization module for the core functionality
of the GAMDL (Generic Apple Music Downloader) application.

Key Responsibilities:
- Initialize core components
- Set up logging
- Configure application-wide settings
- Provide core utility functions
- Manage application state
"""

import sys
import logging
from typing import Any, Dict, Optional
from pathlib import Path

# Local imports
from gamdl.config import config, ConfigManager
from gamdl.constants import (
    AppMetadata,
    LoggingConfig,
    PROJECT_ROOT
)

# External dependencies
import colorlog
import sentry_sdk

# Setup logging before other imports
def setup_logging(
    log_level: str = LoggingConfig.DEFAULT_LEVEL,
    log_dir: Path = PROJECT_ROOT / 'logs'
) -> logging.Logger:
    """
    Configure comprehensive logging with color and file/console output
    
    Args:
        log_level (str): Logging level
        log_dir (Path): Directory for log files
    
    Returns:
        logging.Logger: Configured logger
    """
    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure log file path with timestamp
    from datetime import datetime
    log_file = log_dir / f"gamdl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Create formatters
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s[%(levelname)s] %(asctime)s - %(message)s",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white'
        },
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    logger = logging.getLogger('gamdl')
    logger.setLevel(log_level.upper())
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File Handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

# Initialize Sentry for error tracking
def init_error_tracking() -> Optional[Any]:
    """
    Initialize error tracking and monitoring
    
    Returns:
        Sentry SDK client or None
    """
    sentry_dsn = config.get('sentry.dsn')
    if sentry_dsn:
        return sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=config.get('environment', 'production'),
            release=AppMetadata.VERSION
        )
    return None

# Application State Management
class ApplicationState:
    """
    Centralized application state management
    """
    _instance = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize application state"""
        self.config: Dict[str, Any] = {}
        self.runtime_data: Dict[str, Any] = {}
        self.active_downloads: Dict[str, Any] = {}
        self.system_status: Dict[str, Any] = {
            'cpu_usage': 0,
            'memory_usage': 0,
            'disk_space': 0
        }
    
    def update_system_status(self):
        """Update system resource usage"""
        import psutil
        
        self.system_status['cpu_usage'] = psutil.cpu_percent()
        self.system_status['memory_usage'] = psutil.virtual_memory().percent
        self.system_status['disk_space'] = psutil.disk_usage('/').percent
    
    def track_download(self, download_id: str, metadata: Dict[str, Any]):
        """
        Track active downloads
        
        Args:
            download_id (str): Unique download identifier
            metadata (dict): Download metadata
        """
        self.active_downloads[download_id] = metadata
    
    def remove_download(self, download_id: str):
        """
        Remove completed or failed download
        
        Args:
            download_id (str): Unique download identifier
        """
        self.active_downloads.pop(download_id, None)

# Global Instances
logger = setup_logging()
error_tracker = init_error_tracking()
app_state = ApplicationState()

# Graceful Shutdown Handler
def graceful_shutdown(signum=None, frame=None):
    """
    Handle application shutdown gracefully
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info("Initiating graceful shutdown...")
    
    # Cancel active downloads
    for download_id in list(app_state.active_downloads.keys()):
        try:
            # Implement download cancellation logic
            app_state.remove_download(download_id)
        except Exception as e:
            logger.error(f"Error during download cancellation: {e}")
    
    # Close any open resources
    logger.info("Shutdown complete.")
    sys.exit(0)

# Signal Handling
def register_signal_handlers():
    """Register system signal handlers for graceful shutdown"""
    import signal
    
    signal.signal(signal.SIGINT, graceful_shutdown)   # Ctrl+C
    signal.signal(signal.SIGTERM, graceful_shutdown)  # Termination signal

# Application Initialization
def initialize_application():
    """
    Comprehensive application initialization
    
    Performs:
    - Logging setup
    - Error tracking
    - Signal handling
    - Initial system checks
    """
    try:
        # Log application startup
        logger.info(f"{AppMetadata.NAME} v{AppMetadata.VERSION} starting...")
        
        # Register signal handlers
        register_signal_handlers()
        
        # Perform initial system checks
        app_state.update_system_status()
        
        logger.info("Application initialized successfully.")
    except Exception as e:
        logger.critical(f"Application initialization failed: {e}")
        sys.exit(1)

# Expose key components
__all__ = [
    'logger',
    'error_tracker',
    'app_state',
    'initialize_application',
    'setup_logging',
    'graceful_shutdown'
]

# Auto-initialize on import
initialize_application()
