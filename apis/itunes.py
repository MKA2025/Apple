"""
iTunes API Module

Provides interaction with iTunes API for media metadata retrieval
and additional information about Apple Music content.
"""

import logging
import re
from typing import Dict, Any, Optional, List

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from gamdl.apis import BaseAPI, APICredentials
from gamdl.models import (
    Song, 
    Album, 
    Artist, 
    MusicVideo
)
from gamdl.constants import STOREFRONT_IDS

logger = logging.getLogger(__name__)

class iTunesAPI(BaseAPI):
    """
    iTunes API implementation for metadata retrieval
    """
    
    LOOKUP_BASE_URL = 'https://itunes.apple.com/lookup'
    MUSIC_BASE_URL = 'https://music.apple.com'
    
    def __init__(
        self, 
        credentials: Optional[APICredentials] = None,
        storefront: str = 'us',
        language: str = 'en-US'
    ):
        super().__init__(
            credentials or APICredentials(),
            base_url=self.LOOKUP_BASE_URL
        )
        self.storefront = storefront.upper()
        self.language = language
        self._setup_session()
    
    def _setup_session(self):
        """
        Configure session parameters for iTunes API requests
        """
        try:
            storefront_id = STOREFRONT_IDS.get(self.storefront)
            if not storefront_id:
                raise ValueError(f"Invalid storefront: {self.storefront}")
            
            self._session.params = {
                'country': self.storefront.lower(),
                'lang': self.language
            }
            
            self._session.headers.update({
                'X-Apple-Store-Front': f"{storefront_id} t:music31",
                'User-Agent': 'iTunes/12.0 (Macintosh; OS X 10.15)'
            })
        
        except Exception as e:
            logger.error(f"Session setup error: {e}")
    
    def lookup_resource(
        self, 
        resource_id: str, 
        entity: str = 'album'
    ) -> Optional[Dict[str, Any]]:
        """
        Lookup a resource by its ID
        
        Args:
            resource_id (str): Unique identifier of the resource
            entity (str): Type of resource to lookup
        
        Returns:
            Optional[Dict[str, Any]]: Resource metadata
        """
        try:
            response = self._session.get(
                self.LOOKUP_BASE_URL,
                params={
                    'id': resource_id,
                    'entity': entity
                }
            )
            response.raise_for_status()
            
            result = response.json().get('results', [])
            return result[0] if result else None
        
        except requests.RequestException as e:
            logger.error(f"Resource lookup error: {e}")
            return None
    
    def get_song_details(self, song_id: str) -> Optional[Song]:
        """
        Get detailed song information from iTunes
        
        Args:
            song_id (str): iTunes song ID
        
        Returns:
            Optional[Song]: Song metadata
        """
        result = self.lookup_resource(song_id, 'song')
        return Song.from_itunes_data(result) if result else None
    
    def get_album_details(self, album_id: str) -> Optional[Album]:
        """
        Get detailed album information from iTunes
        
        Args:
            album_id (str): iTunes album ID
        
        Returns:
            Optional[Album]: Album metadata
        """
        result = self.lookup_resource(album_id, 'album')
        return Album.from_itunes_data(result) if result else None
    
    def get_artist_details(self, artist_id: str) -> Optional[Artist]:
        """
        Get detailed artist information from iTunes
        
        Args:
            artist_id (str): iTunes artist ID
        
        Returns:
            Optional[Artist]: Artist metadata
        """
        result = self.lookup_resource(artist_id, 'artist')
        return Artist.from_itunes_data(result) if result else None
    
    def get_music_video_details(self, video_id: str) -> Optional[MusicVideo]:
        """
        Get detailed music video information from iTunes
        
        Args:
            video_id (str): iTunes music video ID
        
        Returns:
            Optional[MusicVideo]: Music video metadata
        """
        result = self.lookup_resource(video_id, 'musicVideo')
        return MusicVideo.from_itunes_data(result) if result else None
    
    def search(
        self, 
        term: str, 
        media_type: str = 'all', 
        limit: int = 25
    ) -> Dict[str, List[Any]]:
        """
        Search iTunes Store
        
        Args:
            term (str): Search query
            media_type (str): Type of media to search
            limit (int): Maximum number of results
        
        Returns:
            Dict[str, List[Any]]: Search results
        """
        try:
            response = self._session.get(
                'https://itunes.apple.com/search',
                params={
                    'term': term,
                    'media': media_type,
                    'limit': limit
                }
            )
            response.raise_for_status()
            
            results = response.json().get('results', [])
            return self._parse_search_results(results)
        
        except requests.RequestException as e:
            logger.error(f"iTunes search error: {e}")
            return {}
    
    def _parse_search_results(self, results: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """
        Parse and categorize search results
        
        Args:
            results (List[Dict[str, Any]]): Raw search results
        
        Returns:
            Dict[str, List[Any]]: Categorized results
        """
        parsed_results = {
            'songs': [],
            'albums': [],
            'artists': [],
            'music_videos': []
        }
        
        for result in results:
            kind = result.get('kind', result.get('wrapperType'))
            
            if kind == 'song':
                parsed_results['songs'].append(Song.from_itunes_data(result))
            elif kind == 'album':
                parsed_results['albums'].append(Album.from_itunes_data(result))
            elif kind == 'artist':
                parsed_results['artists'].append(Artist.from_itunes_data(result))
            elif kind == 'music-video':
                parsed_results['music_videos'].append(MusicVideo.from_itunes_data(result))
        
        return parsed_results

# Public API
__all__ = ['iTunesAPI']
