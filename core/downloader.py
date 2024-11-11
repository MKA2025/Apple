"""
GAMDL Core Downloader Module

Provides advanced downloading capabilities with robust error handling,
progress tracking, and multi-source support.
"""

import asyncio
import concurrent.futures
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import aiohttp
import requests
from tqdm import tqdm

from gamdl.core import logger, app_state
from gamdl.config import config
from gamdl.constants import (
    FileConstants,
    SecurityConstants,
    DownloadStatus,
    MediaType
)

@dataclass
class DownloadTask:
    """
    Represents a single download task with comprehensive metadata
    """
    url: str
    destination: Path
    media_type: MediaType
    task_id: str = field(default_factory=lambda: hashlib.md5(os.urandom(16)).hexdigest())
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class DownloadManager:
    """
    Advanced download management with async support
    """
    def __init__(
        self, 
        max_concurrent_downloads: int = SecurityConstants.MAX_CONCURRENT_DOWNLOADS,
        timeout: int = SecurityConstants.DOWNLOAD_TIMEOUT
    ):
        self.max_concurrent_downloads = max_concurrent_downloads
        self.timeout = timeout
        self.download_semaphore = asyncio.Semaphore(max_concurrent_downloads)
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrent_downloads
        )

    async def download_file(
        self, 
        task: DownloadTask, 
        progress_callback: Optional[Callable] = None
    ) -> DownloadTask:
        """
        Async file download with progress tracking
        
        Args:
            task (DownloadTask): Download task details
            progress_callback (Optional[Callable]): Optional progress update function
        
        Returns:
            DownloadTask: Updated download task
        """
        async def _download_stream():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(task.url, timeout=self.timeout) as response:
                        response.raise_for_status()
                        task.file_size = int(response.headers.get('content-length', 0))
                        
                        task.destination.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(task.destination, 'wb') as f:
                            downloaded = 0
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Update progress
                                task.progress = downloaded / task.file_size if task.file_size else 0
                                
                                if progress_callback:
                                    progress_callback(task)
                
                task.status = DownloadStatus.COMPLETED
                return task
            
            except aiohttp.ClientError as e:
                task.status = DownloadStatus.FAILED
                task.error_message = str(e)
                logger.error(f"Download failed: {e}")
                return task

        async with self.download_semaphore:
            return await _download_stream()

    def download_file_sync(
        self, 
        task: DownloadTask, 
        progress_callback: Optional[Callable] = None
    ) -> DownloadTask:
        """
        Synchronous file download with progress tracking
        
        Args:
            task (DownloadTask): Download task details
            progress_callback (Optional[Callable]): Optional progress update function
        
        Returns:
            DownloadTask: Updated download task
        """
        try:
            response = requests.get(task.url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            task.file_size = int(response.headers.get('content-length', 0))
            task.destination.parent.mkdir(parents=True, exist_ok=True)
            
            with open(task.destination, 'wb') as f, tqdm(
                total=task.file_size,
                unit='iB',
                unit_scale=True,
                desc=task.destination.name
            ) as progress_bar:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    chunk_size = f.write(chunk)
                    downloaded += chunk_size
                    progress_bar.update(chunk_size)
                    
                    # Update task progress
                    task.progress = downloaded / task.file_size if task.file_size else 0
                    
                    if progress_callback:
                        progress_callback(task)
            
            task.status = DownloadStatus.COMPLETED
            return task
        
        except requests.RequestException as e:
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)
            logger.error(f"Synchronous download failed: {e}")
            return task

    async def download_multiple(
        self, 
        tasks: List[DownloadTask], 
        progress_callback: Optional[Callable] = None
    ) -> List[DownloadTask]:
        """
        Download multiple files concurrently
        
        Args:
            tasks (List[DownloadTask]): List of download tasks
            progress_callback (Optional[Callable]): Optional progress update function
        
        Returns:
            List[DownloadTask]: List of completed download tasks
        """
        tasks_coroutines = [
            self.download_file(task, progress_callback) for task in tasks
        ]
        return await asyncio.gather(*tasks_coroutines)

    def create_download_task(
        self, 
        url: str, 
        destination: Union[str, Path], 
        media_type: MediaType, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> DownloadTask:
        """
        Create a standardized download task
        
        Args:
            url (str): Download URL
            destination (Union[str, Path]): File save path
            media_type (MediaType): Type of media being downloaded
            metadata (Optional[Dict[str, Any]]): Additional task metadata
        
        Returns:
            DownloadTask: Configured download task
        """
        task = DownloadTask(
            url=url,
            destination=Path(destination),
            media_type=media_type,
            metadata=metadata or {}
        )
        
        # Register task in application state
        app_state.track_download(task.task_id, task.__dict__)
        
        return task

    def validate_download(self, task: DownloadTask) -> bool:
        """
        Validate downloaded file
        
        Args:
            task (DownloadTask): Completed download task
        
        Returns:
            bool: Whether download is valid
        """
        # Check file size
        if task.file_size and task.destination.stat().st_size != task.file_size:
            logger.warning(f"File size mismatch: {task.destination}")
            return False
        
        # Check file extension
        if task.destination.suffix not in FileConstants.ALLOWED_EXTENSIONS:
            logger.warning(f"Invalid file type: {task.destination.suffix}")
            return False
        
        return True

# Create singleton download manager
download_manager = DownloadManager()

# Expose key components
__all__ = [
    'DownloadTask',
    'DownloadManager', 
    'download_manager',
    'MediaType'
]
