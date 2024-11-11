"""
Download Service Module

Provides centralized download management, tracking, 
and orchestration for various media types and sources.
"""

from __future__ import annotations

import os
import logging
import asyncio
import concurrent.futures
from typing import (
    List, 
    Dict, 
    Any, 
    Optional, 
    Union, 
    Callable
)
from pathlib import Path
from dataclasses import dataclass, field

from gamdl.apis import (
    AppleMusicAPI, 
    SpotifyAPI, 
    YouTubeAPI
)
from gamdl.models import (
    DownloadTask, 
    DownloadStatus, 
    MediaType,
    DownloadConfig
)
from gamdl.services import (
    AuthService, 
    NotificationService
)
from gamdl.utils import (
    SingletonMeta, 
    generate_unique_filename
)

logger = logging.getLogger(__name__)

@dataclass
class DownloadProgress:
    """
    Represents download progress for a specific task
    """
    task_id: str
    total_size: int = 0
    downloaded_size: int = 0
    status: DownloadStatus = DownloadStatus.PENDING
    error: Optional[str] = None
    start_time: Optional[float] = field(default_factory=lambda: None)
    end_time: Optional[float] = field(default_factory=lambda: None)

class DownloadService(metaclass=SingletonMeta):
    """
    Centralized download management service
    """

    def __init__(
        self, 
        auth_service: Optional[AuthService] = None,
        notification_service: Optional[NotificationService] = None,
        max_concurrent_downloads: int = 3,
        download_directory: Optional[Path] = None
    ):
        """
        Initialize download service

        Args:
            auth_service (Optional[AuthService]): Authentication service
            notification_service (Optional[NotificationService]): Notification service
            max_concurrent_downloads (int): Maximum simultaneous downloads
            download_directory (Optional[Path]): Base download directory
        """
        self.auth_service = auth_service or AuthService()
        self.notification_service = notification_service or NotificationService()
        
        self.max_concurrent_downloads = max_concurrent_downloads
        self.download_directory = download_directory or Path.home() / "Downloads" / "Gamdl"
        self.download_directory.mkdir(parents=True, exist_ok=True)

        self._download_tasks: Dict[str, DownloadTask] = {}
        self._download_progress: Dict[str, DownloadProgress] = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrent_downloads
        )

    def _get_api_for_source(self, source: str) -> Union[AppleMusicAPI, SpotifyAPI, YouTubeAPI]:
        """
        Get appropriate API for a download source

        Args:
            source (str): Download source

        Returns:
            Union[AppleMusicAPI, SpotifyAPI, YouTubeAPI]: Corresponding API
        """
        api_map = {
            'apple_music': AppleMusicAPI,
            'spotify': SpotifyAPI,
            'youtube': YouTubeAPI
        }
        
        credentials = self.auth_service.get_credentials(source)
        if not credentials:
            raise ValueError(f"No credentials found for source: {source}")
        
        return api_map[source](credentials)

    def create_download_task(
        self, 
        url: str, 
        media_type: MediaType,
        config: Optional[DownloadConfig] = None
    ) -> DownloadTask:
        """
        Create a new download task

        Args:
            url (str): Media URL
            media_type (MediaType): Type of media to download
            config (Optional[DownloadConfig]): Download configuration

        Returns:
            DownloadTask: Created download task
        """
        task_id = generate_unique_filename()
        download_task = DownloadTask(
            id=task_id,
            url=url,
            media_type=media_type,
            config=config or DownloadConfig()
        )
        
        self._download_tasks[task_id] = download_task
        self._download_progress[task_id] = DownloadProgress(task_id=task_id)
        
        return download_task

    async def download_media(
        self, 
        task_id: str, 
        on_progress: Optional[Callable] = None
    ) -> Optional[Path]:
        """
        Download media for a specific task

        Args:
            task_id (str): Download task ID
            on_progress (Optional[Callable]): Progress callback function

        Returns:
            Optional[Path]: Path to downloaded file
        """
        task = self._download_tasks.get(task_id)
        progress = self._download_progress.get(task_id)
        
        if not task or not progress:
            logger.error(f"Invalid task ID: {task_id}")
            return None

        try:
            # Determine source from URL
            source = self._determine_source(task.url)
            api = self._get_api_for_source(source)
            
            # Update progress
            progress.status = DownloadStatus.DOWNLOADING
            progress.start_time = asyncio.get_event_loop().time()

            # Download based on media type
            download_method_map = {
                MediaType.SONG: self._download_song,
                MediaType.ALBUM: self._download_album,
                MediaType.PLAYLIST: self._download_playlist,
                MediaType.MUSIC_VIDEO: self._download_music_video
            }

            download_method = download_method_map.get(task.media_type)
            if not download_method:
                raise ValueError(f"Unsupported media type: {task.media_type}")

            result = await download_method(api, task, progress, on_progress)
            
            # Update progress
            progress.status = DownloadStatus.COMPLETED
            progress.end_time = asyncio.get_event_loop().time()
            
            return result

        except Exception as e:
            logger.error(f"Download failed: {e}")
            progress.status = DownloadStatus.FAILED
            progress.error = str(e)
            
            # Send error notification
            self.notification_service.send_error_notification(
                f"Download failed: {e}"
            )
            
            return None

    async def _download_song(
        self, 
        api: Union[AppleMusicAPI, SpotifyAPI], 
        task: DownloadTask,
        progress: DownloadProgress,
        on_progress: Optional[Callable] = None
    ) -> Optional[Path]:
        """
        Download a single song

        Args:
            api (Union[AppleMusicAPI, SpotifyAPI]): API instance
            task (DownloadTask): Download task
            progress (DownloadProgress): Download progress
            on_progress (Optional[Callable]): Progress callback

        Returns:
            Optional[Path]: Path to downloaded song
        """
        # Implement song-specific download logic
        song_info = await api.get_song_info(task.url)
        download_path = await api.download_song(
            song_info, 
            self.download_directory, 
            task.config,
            progress_callback=on_progress
        )
        return download_path

    async def _download_album(
        self, 
        api: Union[AppleMusicAPI, SpotifyAPI], 
        task: DownloadTask,
        progress: DownloadProgress,
        on_progress: Optional[Callable] = None
    ) -> Optional[Path]:
        """
        Download an entire album

        Args:
            api (Union[AppleMusicAPI, SpotifyAPI]): API instance
            task (DownloadTask): Download task
            progress (DownloadProgress): Download progress
            on_progress (Optional[Callable]): Progress callback

        Returns:
            Optional[Path]: Path to downloaded album directory
        """
        # Implement album-specific download logic
        album_info = await api.get_album_info(task.url)
        download_path = await api.download_album(
            album_info, 
            self.download_directory, 
            task.config,
            progress_callback=on_progress
        )
        return download_path

    async def _download_playlist(
        self, 
        api: Union[AppleMusicAPI, SpotifyAPI], 
        task: DownloadTask,
        progress: DownloadProgress,
        on_progress: Optional[Callable] = None
    ) -> Optional[Path]:
        """
        Download an entire playlist

        Args:
            api (Union[AppleMusicAPI, SpotifyAPI]): API instance
            task (DownloadTask): Download task
            progress (DownloadProgress): Download progress
            on_progress (Optional[Callable]): Progress callback

        Returns:
            Optional[Path]: Path to downloaded playlist directory
        """
        # Implement playlist-specific download logic
        playlist_info = await api.get_playlist_info(task.url)
        download_path = await api.download_playlist(
            playlist_info, 
            self.download_directory, 
            task.config,
            progress_callback=on_progress
        )
        return download_path

    async def _download_music_video(
        self, 
        api: YouTubeAPI, 
        task: DownloadTask,
        progress: DownloadProgress,
        on_progress: Optional[Callable] = None
    ) -> Optional[Path]:
        """
        Download a music video

        Args:
            api (YouTubeAPI): API instance
            task (DownloadTask): Download task
            progress (DownloadProgress): Download progress
            on_progress (Optional[Callable]): Progress callback

        Returns:
            Optional[Path]: Path to downloaded music video
        """
        # Implement music video-specific download logic
        video_info = await api.get_video_info(task.url)
        download_path = await api.download_video(
            video_info, 
            self.download_directory, 
            task.config,
            progress_callback=on_progress
        )
        return download_path

    def _determine_source(self, url: str) -> str:
        """
        Determine the source of the media from the URL

        Args:
            url (str): Media URL

        Returns:
            str: Source identifier
        """
        if "apple.com" in url:
            return "apple_music"
        elif "spotify.com" in url:
            return "spotify"
        elif "youtube.com" in url or "youtu.be" in url:
            return "youtube"
        else:
            raise ValueError("Unsupported media source")

    def start_download(self, task_id: str, on_progress: Optional[Callable] = None):
        """
        Start the download process for a specific task

        Args:
            task_id (str): Download task ID
            on_progress (Optional[Callable]): Progress callback function
        """
        asyncio.run(self.download_media(task_id, on_progress))

# Public API
__all__ = [
    'DownloadService'
]
