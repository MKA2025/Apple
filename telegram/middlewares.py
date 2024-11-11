"""
Telegram Bot Middlewares Module

Provides advanced middleware functionalities for 
processing and intercepting Telegram bot interactions.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import (
    Any, 
    Awaitable, 
    Callable, 
    Dict, 
    Optional
)
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    BaseHandler,
    ContextTypes,
    Application,
    ExtBot
)

from gamdl.models import (
    UserProfile, 
    ActivityLog,
    RateLimitConfig
)
from gamdl.services import (
    LoggingService,
    UserService,
    CacheService,
    RateLimitService
)
from gamdl.utils import generate_unique_id

class TelegramMiddleware:
    """
    Advanced Telegram Bot Middleware Management
    """

    def __init__(
        self,
        user_service: UserService,
        logging_service: LoggingService,
        cache_service: Optional[CacheService] = None,
        rate_limit_service: Optional[RateLimitService] = None,
        rate_limit_config: Optional[RateLimitConfig] = None
    ):
        """
        Initialize Telegram Middleware

        Args:
            user_service (UserService): User management service
            logging_service (LoggingService): Logging service
            cache_service (Optional[CacheService]): Cache service
            rate_limit_service (Optional[RateLimitService]): Rate limiting service
            rate_limit_config (Optional[RateLimitConfig]): Rate limit configuration
        """
        self.user_service = user_service
        self.logger = logging_service.get_logger(__name__)
        self.cache_service = cache_service
        self.rate_limit_service = rate_limit_service
        self.rate_limit_config = rate_limit_config or RateLimitConfig()

    async def pre_process_middleware(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """
        Pre-process middleware for incoming updates

        Args:
            update (Update): Telegram update
            context (ContextTypes.DEFAULT_TYPE): Bot context

        Returns:
            bool: Whether to continue processing the update
        """
        try:
            # User authentication and tracking
            await self._process_user_authentication(update)

            # Rate limiting
            if not await self._check_rate_limit(update):
                return False

            # Activity logging
            await self._log_activity(update)

            # Security checks
            if not await self._security_checks(update):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Middleware pre-processing error: {e}")
            return False

    async def post_process_middleware(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        result: Any
    ):
        """
        Post-process middleware for processed updates

        Args:
            update (Update): Telegram update
            context (ContextTypes.DEFAULT_TYPE): Bot context
            result (Any): Processing result
        """
        try:
            # Performance tracking
            await self._track_performance(update, result)

            # Additional post-processing logic
            await self._handle_post_processing(update, result)

        except Exception as e:
            self.logger.error(f"Middleware post-processing error: {e}")

    async def _process_user_authentication(self, update: Update):
        """
        Process user authentication and profile management

        Args:
            update (Update): Telegram update
        """
        user = update.effective_user
        if user:
            user_profile = UserProfile(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code
            )
            await self.user_service.create_or_update_user(user_profile)

    async def _check_rate_limit(self, update: Update) -> bool:
        """
        Check and enforce rate limiting

        Args:
            update (Update): Telegram update

        Returns:
            bool: Whether the request is allowed
        """
        if not self.rate_limit_service:
            return True

        user = update.effective_user
        try:
            is_allowed = await self.rate_limit_service.check_rate_limit(
                user_id=user.id,
                config=self.rate_limit_config
            )

            if not is_allowed:
                # Notify user about rate limit
                await update.message.reply_text(
                    "⏳ Rate limit exceeded. Please try again later."
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Rate limit check error: {e}")
            return False

    async def _log_activity(self, update: Update):
        """
        Log user activity

        Args:
            update (Update): Telegram update
        """
        user = update.effective_user
        activity_log = ActivityLog(
            log_id=generate_unique_id(),
            user_id=user.id,
            username=user.username,
            activity_type=self._get_activity_type(update),
            timestamp=datetime.utcnow()
        )
        
        # Log activity (could be sent to database or logging service)
        if self.cache_service:
            await self.cache_service.set(
                f"activity_log_{activity_log.log_id}", 
                activity_log.to_dict()
            )

    def _get_activity_type(self, update: Update) -> str:
        """
        Determine activity type from update

        Args:
            update (Update): Telegram update

        Returns:
            str: Activity type
        """
        if update.message:
            if update.message.text:
                return "text_message"
            elif update.message.photo:
                return "photo_message"
            elif update.message.document:
                return "document_message"
        elif update.callback_query:
            return "callback_query"
        return "unknown"

    async def _security_checks(self, update: Update) -> bool:
        """
        Perform security checks on incoming updates

        Args:
            update (Update): Telegram update

        Returns:
            bool: Whether the update passes security checks
        """
        user = update.effective_user
        
        # Example security checks
        if not user:
            return False

        # Check for spam or suspicious activity
        # Implement your custom security logic here
        return True

    async def _track_performance(self, update: Update, result: Any):
        """
        Track performance of bot interactions

        Args:
            update (Update): Telegram update
            result (Any): Processing result
        """
        # Measure response time and log performance metrics
        processing_time = time.time() - update.message.date.timestamp()
        
        performance_log = {
            "user_id": update.effective_user.id,
            "processing_time": processing_time,
            "result_status": "success" if result else "failed"
        }

        if self.cache_service:
            await self.cache_service.set(
                f"performance_log_{generate_unique_id()}", 
                performance_log
            )

    async def _handle_post_processing(self, update: Update, result: Any):
        """
        Additional post-processing logic

        Args:
            update (Update): Telegram update
            result (Any): Processing result
        """
        # Implement any additional post-processing logic
        # E.g., sending notifications, updating user statistics
        pass

def setup_middlewares(
    application: Application,
    user_service: UserService,
    logging_service: LoggingService,
    cache_service: Optional[CacheService] = None,
    rate_limit_service: Optional[RateLimitService] = None
) -> Application:
    """
    Set up middlewares for Telegram bot application

    Args:
        application (Application): Telegram bot application
        user_service (UserService): User management service
         logging_service (LoggingService): Logging service
        cache_service (Optional[CacheService]): Cache service
        rate_limit_service (Optional[RateLimitService]): Rate limiting service

    Returns:
        Application: Updated Telegram bot application with middlewares
    """
    middleware = TelegramMiddleware(
        user_service=user_service,
        logging_service=logging_service,
        cache_service=cache_service,
        rate_limit_service=rate_limit_service
    )

    application.middleware.append(middleware.pre_process_middleware)
    application.middleware.append(middleware.post_process_middleware)

    return application

# Public API
__all__ = [
    'TelegramMiddleware',
    'setup_middlewares'
          ]
