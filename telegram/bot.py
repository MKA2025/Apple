"""
Telegram Bot Module

Provides advanced Telegram bot functionality with 
modular command handling and user interaction.
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
    BotCommand
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters
)

from gamdl.models import (
    TelegramConfig, 
    TelegramCommandContext,
    TelegramCallbackContext,
    DownloadRequest
)
from gamdl.services import (
    LoggingService, 
    NotificationService,
    CacheService,
    DownloadService
)
from gamdl.utils import SingletonMeta

class TelegramBotHandler:
    """
    Advanced Telegram Bot Command and Interaction Handler
    """

    def __init__(
        self, 
        bot: TelegramBot,
        download_service: DownloadService
    ):
        """
        Initialize Telegram Bot Handler

        Args:
            bot (TelegramBot): Parent Telegram bot instance
            download_service (DownloadService): Download service
        """
        self.bot = bot
        self.download_service = download_service
        self.logger = bot.logger

    async def handle_start(
        self, 
        update: Update, 
        context: TelegramCommandContext
    ) -> None:
        """
        Handle /start command

        Args:
            update (Update): Telegram update
            context (TelegramCommandContext): Command context
        """
        user = update.effective_user
        welcome_message = (
            f"👋 Hello {user.first_name}! Welcome to Gamdl Telegram Bot 🎵\n\n"
            "I can help you download Apple Music content. Send me a link or use commands:\n"
            "/help - Show available commands\n"
            "/download - Download Apple Music content\n"
            "/status - Check bot status"
        )
        
        # Create custom keyboard
        keyboard = [
            [
                InlineKeyboardButton("📥 Download", callback_data="download"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message, 
            reply_markup=reply_markup
        )

    async def handle_help(
        self, 
        update: Update, 
        context: TelegramCommandContext
    ) -> None:
        """
        Handle /help command

        Args:
            update (Update): Telegram update
            context (TelegramCommandContext): Command context
        """
        help_message = (
            "🤖 Gamdl Telegram Bot Help\n\n"
            "Available Commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/download <url> - Download Apple Music content\n"
            "/status - Check bot status\n\n"
            "Supported Content Types:\n"
            "• Songs\n"
            "• Albums\n"
            "• Playlists\n"
            "• Music Videos\n\n"
            "Send a direct Apple Music URL to download!"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🌐 Website", url="https://github.com/your_repo"),
                InlineKeyboardButton("📞 Support", callback_data="support")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_message, 
            reply_markup=reply_markup
        )

    async def handle_download(
        self, 
        update: Update, 
        context: TelegramCommandContext
    ) -> None:
        """
        Handle /download command

        Args:
            update (Update): Telegram update
            context (TelegramCommandContext): Command context
        """
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide an Apple Music URL.\n"
                "Example: /download https://music.apple.com/...",
                reply_markup=self._get_download_help_markup()
            )
            return

        url = context.args[0]
        user = update.effective_user

        try:
            # Create download request
            download_request = DownloadRequest(
                url=url,
                user_id=user.id,
                username=user.username,
                platform='telegram'
            )

            # Process download
            download_result = await self.download_service.process_download(download_request)
            
            if download_result.success:
                await update.message.reply_text(
                    f"✅ Download Completed: {download_result.title}",
                    reply_markup=self._get_download_options_markup(download_result)
                )
            else:
                await update.message.reply_text(
                    f"❌ Download Failed: {download_result.error_message}",
                    reply_markup=self._get_download_help_markup()
                )

        except Exception as e:
            self.logger.error(f"Download error: {e}")
            await update.message.reply_text(
                f"❌ Error processing download: {str(e)}",
                reply_markup=self._get_download_help_markup()
            )

    async def handle_status(
        self, 
        update: Update, 
        context: TelegramCommandContext
    ) -> None:
        """
        Handle /status command

        Args:
            update (Update): Telegram update
            context (TelegramCommandContext): Command context
        """
        status_details = await self._get_bot_status()
        
        status_message = (
            "🤖 Gamdl Bot Status\n"
            f"Version: {status_details['version']}\n"
            f"Uptime: {status_details['uptime']}\n"
            f"Total Downloads: {status_details['total_downloads']}\n"
            f"Active Users: {status_details['active_users']}"
        )
        
        await update.message.reply_text(status_message)

    async def handle_callback_query(
        self, 
        update: Update, 
        context: TelegramCallbackContext
    ) -> None:
        """
        Handle inline keyboard callback queries

        Args:
            update (Update): Telegram update
            context (TelegramCallbackContext): Callback context
        """
        query = update.callback_query
        await query.answer()

        data = query.data
        if data == 'download':
            await query.edit_message_text(
                "Send me an Apple Music URL to download 📥"
            )
        elif data == 'help':
            await self.handle_help(update, context)
        elif data.startswith('download_action_'):
            await self._handle_download_action(query, data)

    async def _handle_download_action(
        self, 
        query: telegram.CallbackQuery, 
        data: str
    ) -> None:
        """
        Handle download-related actions

        Args:
            query (telegram.CallbackQuery): Callback query
            data (str): Callback data
        """
        action = data.split('_')[-1]
        
        if action == 'retry':
            await query.edit_message_text("Please send the URL again.")
        elif action == 'details':
            # Show download details
            pass

    def _get_download_help_markup(self) -> InlineKeyboardMarkup:
        """
        Create download help inline keyboard

        Returns:
            InlineKeyboardMarkup: Inline keyboard markup
        """
        keyboard = [
            [
                InlineKeyboardButton "📥 Download Help", callback_data="help")
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
                InlineKeyboardButton("🔄 Retry", callback_data=f"download_action_retry"),
                InlineKeyboardButton("ℹ️ Details", callback_data=f"download_action_details")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _get_bot_status(self) -> Dict[str, Any]:
        """
        Retrieve bot status information

        Returns:
            Dict[str, Any]: Dictionary containing bot status details
        """
        # Placeholder for actual status retrieval logic
        return {
            "version": "1.0.0",
            "uptime": "24 hours",
            "total_downloads": 150,
            "active_users": 30
        }

# Public API
__all__ = [
    'TelegramBotHandler'
]
