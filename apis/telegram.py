"""
Telegram API Module

Provides interaction with Telegram Bot API for sending notifications,
uploading files, and managing Telegram bot interactions.
"""

import logging
import os
from typing import Optional, Union, List, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from gamdl.apis import BaseAPI, APICredentials
from gamdl.models import TelegramMessage, TelegramFile

logger = logging.getLogger(__name__)

class TelegramAPI(BaseAPI):
    """
    Telegram Bot API implementation for messaging and file sharing
    """
    
    BASE_URL = 'https://api.telegram.org/bot'
    FILE_BASE_URL = 'https://api.telegram.org/file/bot'
    
    def __init__(
        self, 
        credentials: APICredentials,
        chat_id: Optional[str] = None
    ):
        """
        Initialize Telegram Bot API

        Args:
            credentials (APICredentials): Bot token and authentication details
            chat_id (Optional[str]): Default chat/channel ID to send messages
        """
        super().__init__(
            credentials,
            base_url=self.BASE_URL + credentials.token
        )
        self.chat_id = chat_id
    
    def _prepare_request_params(
        self, 
        method: str, 
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Prepare request parameters for Telegram API

        Args:
            method (str): API method to call
            params (Optional[Dict[str, Any]]): Query parameters
            files (Optional[Dict[str, Any]]): Files to upload

        Returns:
            Dict[str, Any]: Prepared request configuration
        """
        request_params = {
            'url': f"{self.base_url}/{method}",
            'params': params or {},
        }
        
        if files:
            request_params['files'] = files
        
        return request_params
    
    def send_message(
        self, 
        text: str, 
        chat_id: Optional[str] = None,
        parse_mode: str = 'HTML',
        disable_web_page_preview: bool = True,
        **kwargs
    ) -> Optional[TelegramMessage]:
        """
        Send a text message via Telegram Bot

        Args:
            text (str): Message text
            chat_id (Optional[str]): Destination chat/channel ID
            parse_mode (str): Message parsing mode
            disable_web_page_preview (bool): Disable link previews
            **kwargs: Additional Telegram message parameters

        Returns:
            Optional[TelegramMessage]: Sent message details
        """
        try:
            params = {
                'chat_id': chat_id or self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': disable_web_page_preview,
                **kwargs
            }
            
            response = self._session.post(
                **self._prepare_request_params('sendMessage', params=params)
            )
            
            response.raise_for_status()
            return TelegramMessage.from_api_response(response.json())
        
        except requests.RequestException as e:
            logger.error(f"Telegram message send error: {e}")
            return None
    
    def send_document(
        self, 
        file_path: Union[str, bytes], 
        chat_id: Optional[str] = None,
        caption: Optional[str] = None,
        **kwargs
    ) -> Optional[TelegramFile]:
        """
        Send a file via Telegram Bot

        Args:
            file_path (Union[str, bytes]): File path or file bytes
            chat_id (Optional[str]): Destination chat/channel ID
            caption (Optional[str]): File caption
            **kwargs: Additional Telegram file upload parameters

        Returns:
            Optional[TelegramFile]: Uploaded file details
        """
        try:
            params = {
                'chat_id': chat_id or self.chat_id,
                'caption': caption
            }
            
            if isinstance(file_path, str):
                files = {'document': open(file_path, 'rb')}
            else:
                files = {'document': file_path}
            
            response = self._session.post(
                **self._prepare_request_params(
                    'sendDocument', 
                    params=params, 
                    files=files
                )
            )
            
            response.raise_for_status()
            return TelegramFile.from_api_response(response.json())
        
        except requests.RequestException as e:
            logger.error(f"Telegram file upload error: {e}")
            return None
    
    def get_file(self, file_id: str) -> Optional[str]:
        """
        Get file download URL by file ID

        Args:
            file_id (str): Telegram file unique identifier

        Returns:
            Optional[str]: File download URL
        """
        try:
            response = self._session.get(
                **self._prepare_request_params(
                    'getFile', 
                    params={'file_id': file_id}
                )
            )
            
            response.raise_for_status()
            file_path = response.json().get('result', {}).get('file_path')
            
            return f"{self.FILE_BASE_URL}{self._credentials.token}/{file_path}" if file_path else None
        
        except requests.RequestException as e:
            logger.error(f"Telegram file retrieval error: {e}")
            return None
    
    def download_file(
        self, 
        file_id: str, 
        destination: Optional[str] = None
    ) -> Optional[str]:
        """
        Download a file from Telegram

        Args:
            file_id (str): Telegram file unique identifier
            destination (Optional[str]): Local file save path

        Returns:
            Optional[str]: Downloaded file path
        """
        try:
            file_url = self.get_file(file_id)
            if not file_url:
                return None
            
            response = requests.get(file_url, stream=True)
            response.raise_for_status()
            
            if not destination:
                destination = os.path.basename(file_url)
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return destination
        
        except requests.RequestException as e:
            logger.error(f"Telegram file download error: {e}")
            return None

# Public API
__all__ = ['TelegramAPI']
