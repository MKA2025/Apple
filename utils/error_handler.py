"""
Advanced Error Handling Module

Provides sophisticated error handling, 
logging, and reporting mechanisms.
"""

from __future__ import annotations

import sys
import traceback
import logging
from typing import (
    Any, 
    Optional, 
    Dict, 
    Union, 
    Callable, 
    Coroutine
)
from functools import wraps
from datetime import datetime

import sentry_sdk
from telegram import Update
from telegram.ext import ContextTypes

from gamdl.models import (
    ErrorLog, 
    NotificationConfig
)
from gamdl.services import (
    LoggingService, 
    NotificationService,
    CacheService
)
from gamdl.utils import generate_unique_id

class GlobalErrorHandler:
    """
    Centralized error handling and management system
    """

    def __init__(
        self, 
        logging_service: LoggingService,
        notification_service: Optional[NotificationService] = None,
        cache_service: Optional[CacheService] = None,
        sentry_dsn: Optional[str] = None,
        notification_config: Optional[NotificationConfig] = None
    ):
        """
        Initialize global error handler

        Args:
            logging_service (LoggingService): Logging service
            notification_service (Optional[NotificationService]): Notification service
            cache_service (Optional[CacheService]): Cache service
            sentry_dsn (Optional[str]): Sentry DSN for error tracking
            notification_config (Optional[NotificationConfig]): Notification configuration
        """
        self.logger = logging_service.get_logger(__name__)
        self.notification_service = notification_service
        self.cache_service = cache_service
        self.notification_config = notification_config or NotificationConfig()

        # Initialize Sentry if DSN is provided
        if sentry_dsn:
            sentry_sdk.init(dsn=sentry_dsn)

    def handle_exception(
        self, 
        exception: Exception, 
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorLog:
        """
        Centralized exception handling method

        Args:
            exception (Exception): Caught exception
            context (Optional[Dict[str, Any]]): Additional context information

        Returns:
            ErrorLog: Detailed error log
        """
        error_id = generate_unique_id()
        error_log = ErrorLog(
            error_id=error_id,
            error_type=type(exception).__name__,
            error_message=str(exception),
            timestamp=datetime.utcnow(),
            traceback=traceback.format_exc(),
            context=context or {}
        )

        # Log error
        self.logger.error(
            f"Error ID: {error_id}\n"
            f"Type: {error_log.error_type}\n"
            f"Message: {error_log.error_message}\n"
            f"Traceback: {error_log.traceback}"
        )

        # Cache error log
        if self.cache_service:
            self._cache_error_log(error_log)

        # Send notification
        self._send_error_notification(error_log)

        # Report to Sentry
        self._report_to_sentry(error_log)

        return error_log

    def _cache_error_log(self, error_log: ErrorLog):
        """
        Cache error log in storage

        Args:
            error_log (ErrorLog): Error log to cache
        """
        if self.cache_service:
            self.cache_service.set(
                f"error_log_{error_log.error_id}", 
                error_log.to_dict(),
                expiration=timedelta(days=7)
            )

    def _send_error_notification(self, error_log: ErrorLog):
        """
        Send error notifications

        Args:
            error_log (ErrorLog): Error log to notify about
        """
        if self.notification_service and self.notification_config.send_error_notifications:
            try:
                self.notification_service.send_error_notification(
                    error_log, 
                    self.notification_config
                )
            except Exception as notify_error:
                self.logger.error(f"Error sending notification: {notify_error}")

    def _report_to_sentry(self, error_log: ErrorLog):
        """
        Report error to Sentry

        Args:
            error_log (ErrorLog): Error log to report
        """
        try:
            sentry_sdk.capture_exception(
                error=error_log.error_message,
                extra={
                    "error_id": error_log.error_id,
                    "context": error_log.context
                }
            )
        except Exception as sentry_error:
            self.logger.error(f"Sentry reporting error: {sentry_error}")

def error_handler(
    logging_service: LoggingService,
    notification_service: Optional[NotificationService] = None
) -> Callable:
    """
    Decorator for handling exceptions in functions

    Args:
        logging_service (LoggingService): Logging service
        notification_service (Optional[NotificationService]): Notification service

    Returns:
        Callable: Decorated function
    """
    def decorator(func: Union[Callable, Coroutine]) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            error_handler_instance = GlobalErrorHandler(
                logging_service, 
                notification_service
            )
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Create context with function details
                context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
                
                # Handle the exception
                error_log = error_handler_instance.handle_exception(
                    e, 
                    context
                )
                
                # Optional: Re-raise or handle based on requirements
                raise
        
        return wrapper
    return decorator

def telegram_error_handler(
    logging_service: LoggingService,
    notification_service: Optional[NotificationService] = None
):
    """
    Telegram-specific error handler

    Args:
        logging_service (LoggingService): Logging service
        notification_service (Optional[NotificationService]): Notification service
    """
    error_handler_instance = GlobalErrorHandler(
        logging_service, 
        notification_service
    )

    async def handle_error(
        update: Optional[Update], 
        context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Handle Telegram-specific errors

        Args:
            update (Optional[Update]): Telegram update
            context (ContextTypes.DEFAULT_TYPE): Bot context
        """
        try:
            # Extract error from context
            error = context.error
            if not error:
                return

            # Prepare context
            error_context = {
                "update": str(update),
                "user": update.effective_user.id if update and update.effective_user else None,
                "chat": update.effective_chat.id if update and update.effective_chat else None
            }

            # Handle the exception
            error_handler_instance.handle_exception(
                error, 
                error_context
            )

            # Optional: Send error message to user
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ An unexpected error occurred. Our team has been notified."
                )

        except Exception as handler_error:
            # Fallback error logging
            logging.error(f"Telegram error handler failed: {handler_error}")

    return handle_error

# Public API
__all__ = [
    'GlobalErrorHandler',
    'error_handler',
    'telegram_error_handler'
              ]
