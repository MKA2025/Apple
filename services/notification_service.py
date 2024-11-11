"""
Notification Service Module

Provides multi-channel notification capabilities 
including email, desktop, SMS, and webhook notifications.
"""

from __future__ import annotations

import asyncio
import smtplib
import platform
import logging
from typing import (
    Optional, 
    List, 
    Dict, 
    Any, 
    Union
)
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
import telegram
import slack_sdk
import twilio.rest

from gamdl.models import (
    NotificationConfig, 
    NotificationType, 
    NotificationChannel
)
from gamdl.utils import SingletonMeta

class NotificationService(metaclass=SingletonMeta):
    """
    Advanced multi-channel notification service
    """

    def __init__(
        self, 
        config: Optional[NotificationConfig] = None
    ):
        """
        Initialize notification service

        Args:
            config (Optional[NotificationConfig]): Notification configuration
        """
        self.config = config or NotificationConfig()
        self.logger = logging.getLogger(__name__)

        # Initialize notification clients
        self._init_email_client()
        self._init_sms_client()
        self._init_telegram_client()
        self._init_slack_client()
        self._init_desktop_notification()
        self._init_webhooks()

    def _init_email_client(self):
        """
        Initialize email notification client
        """
        if not self.config.email_config:
            self.email_client = None
            return

        try:
            self.email_client = smtplib.SMTP(
                self.config.email_config.smtp_server, 
                self.config.email_config.smtp_port
            )
            self.email_client.starttls()
            self.email_client.login(
                self.config.email_config.username, 
                self.config.email_config.password
            )
        except Exception as e:
            self.logger.error(f"Email client initialization failed: {e}")
            self.email_client = None

    def _init_sms_client(self):
        """
        Initialize SMS notification client
        """
        if not self.config.sms_config:
            self.sms_client = None
            return

        try:
            self.sms_client = twilio.rest.Client(
                self.config.sms_config.account_sid,
                self.config.sms_config.auth_token
            )
        except Exception as e:
            self.logger.error(f"SMS client initialization failed: {e}")
            self.sms_client = None

    def _init_telegram_client(self):
        """
        Initialize Telegram notification client
        """
        if not self.config.telegram_config:
            self.telegram_client = None
            return

        try:
            self.telegram_client = telegram.Bot(
                token=self.config.telegram_config.bot_token
            )
        except Exception as e:
            self.logger.error(f"Telegram client initialization failed: {e}")
            self.telegram_client = None

    def _init_slack_client(self):
        """
        Initialize Slack notification client
        """
        if not self.config.slack_config:
            self.slack_client = None
            return

        try:
            self.slack_client = slack_sdk.WebClient(
                token=self.config.slack_config.bot_token
            )
        except Exception as e:
            self.logger.error(f"Slack client initialization failed: {e}")
            self.slack_client = None

    def _init_desktop_notification(self):
        """
        Initialize desktop notification system
        """
        try:
            system = platform.system()
            if system == "Darwin":
                import pync
                self.desktop_notifier = pync.notify
            elif system == "Windows":
                import win10toast
                self.desktop_notifier = win10toast.ToastNotifier().show_toast
            elif system == "Linux":
                import notify2
                notify2.init("Gamdl")
                self.desktop_notifier = notify2.Notification
            else:
                self.desktop_notifier = None
        except ImportError:
            self.desktop_notifier = None
            self.logger.warning("Desktop notifications not supported")

    def _init_webhooks(self):
        """
        Initialize webhook notification clients
        """
        self.webhook_clients = {}
        if self.config.webhooks:
            for name, webhook_url in self.config.webhooks.items():
                self.webhook_clients[name] = webhook_url

    async def send_notification(
        self, 
        message: str, 
        title: Optional[str] = None,
        notification_type: NotificationType = NotificationType.INFO,
        channels: Optional[List[NotificationChannel]] = None
    ):
        """
        Send notifications through multiple channels

        Args:
            message (str): Notification message
            title (Optional[str]): Notification title
            notification_type (NotificationType): Type of notification
            channels (Optional[List[NotificationChannel]]): Notification channels
        """
        channels = channels or list(NotificationChannel)
        
        notification_tasks = []
        for channel in channels:
            task = asyncio.create_task(
                self._send_channel_notification(
                    channel, message, title, notification_type
                )
            )
            notification_tasks.append(task)
        
        await asyncio.gather(*notification_tasks)

    async def _send_channel_notification(
        self, 
        channel: NotificationChannel, 
        message: str, 
        title: Optional[str] = None,
        notification_type: NotificationType = NotificationType.INFO
    ):
        """
        Send notification through a specific channel

        Args:
            channel (NotificationChannel): Notification channel
            message (str): Notification message
            title (Optional[str]): Notification title
            notification_type (NotificationType): Type of notification
        """
        try:
            if channel == NotificationChannel.EMAIL and self.email_client:
                await self._send_email_notification(message, title, notification_type)
            
            elif channel == NotificationChannel.SMS and self.sms_client:
                await self._send_sms_notification(message, title)
            
            elif channel == NotificationChannel.TELEGRAM and self.telegram_client:
                await self._send_telegram_notification(message, title)
            
            elif channel == NotificationChannel.SLACK and self.slack_client:
                await self._send_slack_notification(message, title)
            
            elif channel == NotificationChannel.DESKTOP and self.desktop_notifier:
                await self._send_desktop_notification(message, title, notification_type)
            
            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook_notifications(message, title, notification_type)

        except Exception as e:
            self.logger.error(f"Failed to send notification via {channel}: {e}")

    async def _send_email_notification(
        self, 
        message: str, 
        title: Optional[str] = None,
        notification_type: NotificationType = NotificationType.INFO
    ):
        """
        Send email notification

        Args:
            message (str): Email message
            title (Optional[str]): Email subject
            notification_type (NotificationType): Type of notification
        """
        if not self.email_client or not self.config.email_config:
            return

        msg = MIMEMultipart()
        msg['From'] = self.config.email_config.username
        msg['To'] = self.config.email_config.recipient
        msg['Subject'] = title or f"Gamdl {notification_type.value.capitalize()} Notification"
        
        msg.attach(MIMEText(message, 'plain'))
        
        await asyncio.to_thread(
            self.email_client.send_message, 
            msg
        )

    async def _send_sms_notification(
        self, 
        message: str, 
        title: Optional[str] = None
    ):
        """ Send SMS notification

        Args:
            message (str): SMS message
            title (Optional[str]): SMS subject
        """
        if not self.sms_client or not self.config.sms_config:
            return

        await asyncio.to_thread(
            self.sms_client.messages.create,
            body=message,
            from_=self.config.sms_config.from_number,
            to=self.config.sms_config.recipient
        )

    async def _send_telegram_notification(
        self, 
        message: str, 
        title: Optional[str] = None
    ):
        """
        Send Telegram notification

        Args:
            message (str): Telegram message
            title (Optional[str]): Telegram title
        """
        if not self.telegram_client or not self.config.telegram_config:
            return

        await asyncio.to_thread(
            self.telegram_client.send_message,
            chat_id=self.config.telegram_config.chat_id,
            text=message
        )

    async def _send_slack_notification(
        self, 
        message: str, 
        title: Optional[str] = None
    ):
        """
        Send Slack notification

        Args:
            message (str): Slack message
            title (Optional[str]): Slack title
        """
        if not self.slack_client or not self.config.slack_config:
            return

        await asyncio.to_thread(
            self.slack_client.chat_postMessage,
            channel=self.config.slack_config.channel,
            text=message
        )

    async def _send_desktop_notification(
        self, 
        message: str, 
        title: Optional[str] = None,
        notification_type: NotificationType = NotificationType.INFO
    ):
        """
        Send desktop notification

        Args:
            message (str): Notification message
            title (Optional[str]): Notification title
            notification_type (NotificationType): Type of notification
        """
        if self.desktop_notifier:
            if platform.system() == "Darwin":
                self.desktop_notifier(title or "Notification", message)
            elif platform.system() == "Windows":
                self.desktop_notifier(title or "Notification", message, duration=10)
            elif platform.system() == "Linux":
                notification = self.desktop_notifier(title or "Notification", message)
                notification.show()

    async def _send_webhook_notifications(
        self, 
        message: str, 
        title: Optional[str] = None,
        notification_type: NotificationType = NotificationType.INFO
    ):
        """
        Send notifications through webhooks

        Args:
            message (str): Notification message
            title (Optional[str]): Notification title
            notification_type (NotificationType): Type of notification
        """
        for name, webhook_url in self.webhook_clients.items():
            payload = {
                'text': f"{title or 'Notification'}: {message}",
                'type': notification_type.value
            }
            await asyncio.to_thread(requests.post, webhook_url, json=payload)

# Public API
__all__ = [
    'NotificationService'
          ]
