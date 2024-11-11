"""
Telegram Bot Handlers Module

Provides advanced and modular handlers for 
different types of Telegram bot interactions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import (
    Optional, 
    Dict, 
    Any, 
    List, 
    Callable, 
    Coroutine, 
    Union
)
from datetime import datetime

import telegram
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

from gamdl.models import (
    TelegramConfig, 
    TelegramCommandContext,
    TelegramCallbackContext,
    DownloadRequest,
    UserProfile
)
from gamdl.services import (
    LoggingService, 
    NotificationService,
    CacheService,
    DownloadService,
    UserService
)
from gamdl.utils import (
    validate_apple_music_url,
    generate_unique_id
)

class TelegramHandlers:
    """
    Advanced Telegram Bot Interaction Handlers
    """

    # Conversation states
    (
        START,
        WAITING_FOR_URL,
        CONFIRM_DOWNLOAD,
        DOWNLOAD_OPTIONS,
        SETTINGS
    ) = range(5)

    def __init__(
        self, 
        config: TelegramConfig,
        download_service: DownloadService,
        user_service: UserService,
        logging_service: LoggingService,
        notification_service: Optional[NotificationService] = None
    ):
        """
        Initialize Telegram Handlers

        Args:
            config (TelegramConfig): Telegram configuration
            download_service (DownloadService): Download service
            user_service (UserService): User management service
            logging_service (LoggingService): Logging service
            notification_service (Optional[NotificationService]): Notification service
        """
        self.config = config
        self.download_service = download_service
        self.user_service = user_service
        self.logger = logging_service.get_logger(__name__)
        self.notification_service = notification_service

    async def start_handler(
        self, 
        update: Update, 
        context: TelegramCommandContext
    ) -> int:
        """
        Handle /start command and initiate user interaction

        Args:
            update (Update): Telegram update
            context (TelegramCommandContext): Command context

        Returns:
            int: Conversation state
        """
        user = update.effective_user
        
        # Create or update user profile
        user_profile = UserProfile(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        await self.user_service.create_or_update_user(user_profile)

        welcome_message = (
            f"👋 Welcome {user.first_name}! I'm your Apple Music Download Assistant 🎵\n\n"
            "Send me an Apple Music URL, and I'll help you download it!"
        )

        keyboard = [
            [
                InlineKeyboardButton("📥 Download", callback_data="start_download"),
                InlineKeyboardButton("⚙️ Settings", callback_data="start_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            welcome_message, 
            reply_markup=reply_markup
        )

        return self.WAITING_FOR_URL

    async def url_handler(
        self, 
        update: Update, 
        context: TelegramCommandContext
    ) -> int:
        """
        Handle incoming URL for download

        Args:
            update (Update): Telegram update
            context (TelegramCommandContext): Command context

        Returns:
            int: Conversation state
        """
        url = update.message.text
        user = update.effective_user

        # Validate Apple Music URL
        if not validate_apple_music_url(url):
            await update.message.reply_text(
                "❌ Invalid Apple Music URL. Please try again.",
                reply_markup=self._get_download_help_markup()
            )
            return self.WAITING_FOR_URL

        try:
            # Prepare download request
            download_request = DownloadRequest(
                url=url,
                user_id=user.id,
                username=user.username,
                request_id=generate_unique_id(),
                timestamp=datetime.utcnow()
            )

            # Analyze download details
            download_preview = await self.download_service.preview_download(download_request)

            if not download_preview.valid:
                await update.message.reply_text(
                    f"❌ Unable to process URL: {download_preview.error_message}",
                    reply_markup=self._get_download_help_markup()
                )
                return self.WAITING_FOR_URL

            # Store download request in context
            context.user_data['download_request'] = download_request
            context.user_data['download_preview'] = download_preview

            # Confirm download keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm", callback_data="confirm_download"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_download")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"📊 Download Preview:\n"
                f"Title: {download_preview.title}\n"
                f"Type: {download_preview.content_type}\n"
                f"Tracks: {download_preview.track_count}\n"
                "Do you want to proceed?",
                reply_markup=reply_markup
            )

            return self.CONFIRM_DOWNLOAD

        except Exception as e:
            self.logger.error(f"URL processing error: {e}")
            await update.message.reply_text(
                "❌ An error occurred. Please try again.",
                reply_markup=self._get_download_help_markup()
            )
            return self.WAITING_FOR_URL

    async def confirm_download_handler(
        self, 
        update: Update, 
        context: TelegramCallbackContext
    ) -> int:
        """
        Handle download confirmation

        Args:
            update (Update): Telegram update
            context (TelegramCallbackContext): Callback context

        Returns:
            int: Conversation state
        """
        query = update.callback_query
        await query.answer()

        if query.data == "confirm_download":
            download_request = context.user_data.get('download_request')
            download_preview = context.user_data.get('download_preview')

            if not download_request or not download_preview:
                await query.edit_message_text("❌ Download request lost. Please start over.")
                return self.START

            try:
                # Process download
                download_result = await self.download_service.process_download(download_request)

                if download_result.success:
                    await query.edit_message_text(
                        f"✅ Download Completed:\n"
                        f"Title: {download_result.title}\n"
                        f"Tracks: {download_result.track_count}",
                        reply_markup=self._get_download_options_markup(download_result)
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Download Failed: {download_result.error_message}",
                        reply_markup=self._get_download_help_markup()
                    )

                return self.DOWNLOAD_OPTIONS

            except Exception as e:
                self.logger.error(f"Download processing error: {e}")
                await query.edit_message_text(
                    "❌ An unexpected error occurred.",
                    reply_markup=self ```python
                    _get_download_help_markup()
                )
                return self.START

        elif query.data == "cancel_download":
            await query.edit_message_text("❌ Download canceled. You can send a new URL anytime.")
            return self.START

    async def download_options_handler(
        self, 
        update: Update, 
        context: TelegramCallbackContext
    ) -> int:
        """
        Handle download options after completion

        Args:
            update (Update): Telegram update
            context (TelegramCallbackContext): Callback context

        Returns:
            int: Conversation state
        """
        query = update.callback_query
        await query.answer()

        # Handle download options (e.g., retry, details)
        if query.data == "retry_download":
            await query.edit_message_text("Please send the URL again.")
            return self.WAITING_FOR_URL
        elif query.data == "download_details":
            # Show download details (placeholder)
            await query.edit_message_text("Here are the download details...")
            return self.START

    def _get_download_help_markup(self) -> InlineKeyboardMarkup:
        """
        Create download help inline keyboard

        Returns:
            InlineKeyboardMarkup: Inline keyboard markup
        """
        keyboard = [
            [
                InlineKeyboardButton("📥 Download Help", callback_data="help")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_download_options_markup(self, download_result: Any) -> InlineKeyboardMarkup:
        """
        Create download options inline keyboard

        Args:
            download_result (Any): Result of the download process

        Returns:
            InlineKeyboardMarkup: Inline keyboard markup
        """
        keyboard = [
            [
                InlineKeyboardButton("🔄 Retry", callback_data="retry_download"),
                InlineKeyboardButton("ℹ️ Details", callback_data="download_details")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

# Public API
__all__ = [
    'TelegramHandlers'
]
