"""
Logging Service Module

Provides advanced logging capabilities with multiple 
output streams, log rotation, and custom formatting.
"""

from __future__ import annotations

import os
import sys
import json
import logging
import asyncio
import traceback
from typing import (
    Optional, 
    Union, 
    Dict, 
    Any, 
    List
)
from pathlib import Path
from datetime import datetime
from logging.handlers import (
    RotatingFileHandler, 
    TimedRotatingFileHandler
)

from gamdl.models import (
    LogConfig, 
    LogLevel, 
    LogFormat, 
    LogDestination
)
from gamdl.utils import SingletonMeta

class ColorFormatter(logging.Formatter):
    """
    Custom colored log formatter
    """
    COLORS = {
        'DEBUG': '\033[94m',    # Blue
        'INFO': '\033[92m',     # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'CRITICAL': '\033[1;31m'  # Bold Red
    }
    RESET = '\033[0m'

    def format(self, record):
        """
        Format log record with color
        """
        log_message = super().format(record)
        color = self.COLORS.get(record.levelname, self.RESET)
        return f"{color}{log_message}{self.RESET}"

class JSONLogFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging
    """
    def format(self, record):
        """
        Convert log record to JSON
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'exception': None
        }

        if record.exc_info:
            log_data['exception'] = {
                'type': type(record.exc_info[1]).__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_data)

class LoggingService(metaclass=SingletonMeta):
    """
    Advanced logging service with multiple output streams
    """

    def __init__(
        self, 
        config: Optional[LogConfig] = None
    ):
        """
        Initialize logging service

        Args:
            config (Optional[LogConfig]): Logging configuration
        """
        self.config = config or LogConfig()
        self._loggers: Dict[str, logging.Logger] = {}
        self._log_directory = Path(self.config.log_directory)
        self._log_directory.mkdir(parents=True, exist_ok=True)

        # Setup root logger
        self._root_logger = logging.getLogger()
        self._root_logger.setLevel(self._convert_log_level(self.config.default_level))

        # Initialize logging handlers
        self._setup_log_handlers()

    def _convert_log_level(self, level: Union[LogLevel, str]) -> int:
        """
        Convert LogLevel enum to Python logging level

        Args:
            level (Union[LogLevel, str]): Log level

        Returns:
            int: Python logging level
        """
        level_map = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL
        }
        return level_map.get(level, logging.INFO)

    def _setup_log_handlers(self):
        """
        Setup log handlers based on configuration
        """
        # Console Handler
        if LogDestination.CONSOLE in self.config.destinations:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self._convert_log_level(self.config.default_level))
            
            if self.config.log_format == LogFormat.COLOR:
                formatter = ColorFormatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            elif self.config.log_format == LogFormat.JSON:
                formatter = JSONLogFormatter()
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            
            console_handler.setFormatter(formatter)
            self._root_logger.addHandler(console_handler)

        # File Handler
        if LogDestination.FILE in self.config.destinations:
            log_file_path = self._log_directory / 'gamdl.log'
            
            if self.config.log_rotation == 'size':
                file_handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=self.config.max_log_size * 1024 * 1024,  # Convert MB to bytes
                    backupCount=self.config.max_backup_count
                )
            else:
                file_handler = TimedRotatingFileHandler(
                    log_file_path,
                    when='midnight',
                    interval=1,
                    backupCount=self.config.max_backup_count
                )

            file_handler.setLevel(self._convert_log_level(self.config.default_level))
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self._root_logger.addHandler(file_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get or create a named logger

        Args:
            name (str): Logger name

        Returns:
            logging.Logger: Configured logger
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(self._convert_log_level(self.config.default_level))
            self._loggers[name] = logger
        return self._loggers[name]

    def log(
        self, 
        level: Union[LogLevel, str], 
        message: str, 
        logger_name: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Log a message with specified level

        Args:
            level (Union[LogLevel, str]): Log level
            message (str): Log message
            logger_name (Optional[str]): Logger name
            extra (Optional[Dict[str, Any]]): Additional log context
        """
        logger = self.get_logger(logger_name or 'root')
        log_method = getattr(logger, level.lower())
        log_method(message, extra=extra)

    def log_exception(
        self, 
        exception: Exception, 
        logger_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log an exception with detailed information

        Args:
            exception (Exception): Exception to log
            logger_name (Optional[str]): Logger name
            context (Optional[Dict[str, Any]]): Additional context
        """
        logger = self.get_logger(logger_name or 'root')
        logger.exception(
            f"Exception occurred: {str(exception)}",
            extra={
                'context': context or {},
                'traceback': traceback.format_exc()
            }
        )

    async def async_log(
        self, 
        level: Union[LogLevel, str], 
        message: str, 
        logger_name: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Asynchronous logging method

        Args:
            level (Union[LogLevel, str]): Log level
            message (str): Log message
            logger_name (Optional[str]): Logger name
            extra (Optional[Dict[str, Any]]): Additional log context
        """
        await asyncio.to_thread(self.log, level, message, logger_name, extra)

# Public API
__all__ = [
    'LoggingService'
      ]
