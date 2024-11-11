"""
Apple Music API Module

Provides comprehensive interaction with Apple Music API for
media retrieval, search, and metadata management.
"""

import base64
import json
import logging
import re
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from gamdl.apis import BaseAPI, APICredentials
from gamdl.models import (
    Song, 
    Album, 
    Artist, 
    Playlist, 
    MusicVideo
)
from gamdl.utils import (
    generate_jwt, 
    parse_apple_music_url
)

logger = logging.getLogger(__name__)

class AppleMusicAPI(BaseAPI):
    """
    Advanced Apple Music API implementation
    """
    
    def __init__(
        self, 
        credentials: APICredentials,
        storefront: str = 'us',
        language: str = 'en-US'
    ):
        super().__init__(
            credentials,
            base_url='https://amp-api.music.apple.com/v1'
        )
        self.storefront = storefront
        self.language = language
        self._media_user_token = None
        self._last_token_refresh = 0
    
    def authenticate(self) -> bool:
        """
        Authenticate with Apple Music API
        
        Returns:
            bool: Authentication status
        """
        try:
            # Generate JWT for authentication
            jwt_token = generate_jwt(
                self.credentials.client_id, 
                self.credentials.client_secret
            )
            
            # Prepare authentication request
            auth_response = self._session.post(
                'https://api.music.apple.com/v1/catalog',
                headers={
                    'Authorization': f'Bearer {jwt_token}',
                    'Music-User-Token': ''
                },
                json={'platform': 'web'}
            )
            
            # Extract media user token
            if auth_response.status_code == 200:
                self._media_user_token = auth_response.headers.get('Music-User-Token')
                self._last_token_refresh = time.time()
                return True
            
            logger.error(f"Authentication failed: {auth_response.text}")
            return False
        
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare headers for Apple Music API requests
        
        Returns:
            Dict[str, str]: Request headers
        """
        # Refresh token if needed
        current_time = time.time()
        if current_time - self._last_token_refresh > 3600:
            self.authenticate()
        
        return {
            'Authorization': f'Bearer {self.credentials.access_token}',
            'Music-User-Token': self._media_user_token,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'GAMDL Apple Music Client/1.0'
        }
    
    def get_song(self, song_id: str) -> Optional[Song]:
        """
        Retrieve detailed song information
        
        Args:
            song_id (str): Apple Music song ID
        
        Returns:
            Optional[Song]: Song metadata
        """
        try:
            response = self._session.get(
                f'{self.base_url}/catalog/{self.storefront}/songs/{song_id}',
                headers=self._prepare_headers(),
                params={
                    'l': self.language,
                    'include': 'lyrics,artists,albums'
                }
            )
            response.raise_for_status()
            
            song_data = response.json()['data'][0]
            return Song.from_apple_music_data(song_data)
        
        except requests.RequestException as e:
            logger.error(f"Song retrieval error: {e}")
            return None
    
    def get_album(self, album_id: str) -> Optional[Album]:
        """
        Retrieve detailed album information
        
        Args:
            album_id (str): Apple Music album ID
        
        Returns:
            Optional[Album]: Album metadata
        """
        try:
            response = self._session.get(
                f'{self.base_url}/catalog/{self.storefront}/albums/{album_id}',
                headers=self._prepare_headers(),
                params={
                    'l': self.language,
                    'include': 'tracks,artists'
                }
            )
            response.raise_for_status()
            
            album_data = response.json()['data'][0]
            return Album.from_apple_music_data(album_data)
        
        except requests.RequestException as e:
            logger.error(f"Album retrieval error: {e}")
            return None
    
    def search(
        self, 
        query: str, 
        types: List[str] = ['songs', 'albums', 'artists'],
        limit: int = 25
    ) -> Dict[str, List[Any]]:
        """
        Perform advanced search across multiple media types
        
        Args:
            query (str): Search query
            types (List[str]): Media types to search
            limit (int): Maximum results per type
        
        Returns:
            Dict[str, List[Any]]: Search results
        """
        try:
            response = self._session.get(
                f'{self.base_url}/catalog/{self.storefront}/search',
                headers=self._prepare_headers(),
                params={
                    'term': query,
                    'types': ','.join(types),
                    'limit': limit,
                    'l': self.language
                }
            )
            response.raise_for_status()
            
            results = response.json().get('results', {})
            return {
                media_type: [
                    self._convert_search_result(item, media_type)
                    for item in results.get(media_type, {}).get('data', [])
                ]
                for media_type in types
            }
        
        except requests.RequestException as e:
            logger.error(f"Search error: {e}")
            return {}
    
    def _convert_search_result(
        self, 
        item: Dict[str, Any], 
        media_type: str
    ) -> Any:
        """
        Convert search result to appropriate model
        
        Args:
            item (Dict[str, Any]): Search result item
            media_type (str): Type of media
        
        Returns:
            Any: Converted model instance
        """
        conversion_map = {
            'songs': Song.from_apple_music_data,
            'albums': Album.from_apple_music_data,
            'artists': Artist.from_apple_music_data
        }
        
        return conversion_map.get(media_type, lambda x: x)(item)
    
    def get_playlist(self, playlist_id: str) -> Optional[Playlist]:
        """
        Retrieve detailed playlist information
        
        Args:
            playlist_id (str): Apple Music playlist ID
        
        Returns:
            Optional[Playlist]: Playlist metadata
        """
        try:
            response = self._session.get(
                f'{self.base_url}/catalog/{self.storefront}/playlists/{playlist_id}',
                headers=self._prepare_headers(),
                params={
                    'l': self.language,
                    'include': 'tracks'
                }
            )
            response.raise_for_status()
            
            playlist_data = response.json()['data'][0]
            return Playlist.from_apple_music_data(playlist_data)
        
        except requests.RequestException as e:
            logger.error(f"Playlist retrieval error: {e}")
            return None
    
    def get_music_video(self, video_id: str) -> Optional[MusicVideo]: """
        Retrieve detailed music video information
        
        Args:
            video_id (str): Apple Music video ID
        
        Returns:
            Optional[MusicVideo]: Music video metadata
        """
        try:
            response = self._session.get(
                f'{self.base_url}/catalog/{self.storefront}/music-videos/{video_id}',
                headers=self._prepare_headers(),
                params={
                    'l': self.language
                }
            )
            response.raise_for_status()
            
            video_data = response.json()['data'][0]
            return MusicVideo.from_apple_music_data(video_data)
        
        except requests.RequestException as e:
            logger.error(f"Music video retrieval error: {e}")
            return None

# Public API
__all__ = [
    'AppleMusicAPI'
]
     def get_music_video(self, video_id: str) -> Optional[MusicVideo]:
    """
    Retrieve detailed music video information
    
    Args:
        video_id (str): Apple Music video ID
    
    Returns:
        Optional[MusicVideo]: Music video metadata
    """
    try:
        response = self._session.get(
            f'{self.base_url}/catalog/{self.storefront}/music-videos/{video_id}',
            headers=self._prepare_headers(),
            params={
                'l': self.language
            }
        )
        response.raise_for_status()
        
        video_data = response.json()['data'][0]
        return MusicVideo.from_apple_music_data(video_data)
    
    except requests.RequestException as e:
        logger.error(f"Music video retrieval error: {e}")
        return None
