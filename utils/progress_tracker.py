"""
Advanced Progress Tracking Utility

Provides sophisticated progress tracking mechanisms 
for long-running tasks with multiple features.
"""

from __future__ import annotations

import asyncio
import time
import json
from typing import (
    Any, 
    Dict, 
    List, 
    Optional, 
    Union, 
    Callable, 
    Coroutine
)
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum, auto

import aiofiles
from tqdm import tqdm

class ProgressStatus(Enum):
    """
    Enumeration of possible progress statuses
    """
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    PAUSED = auto()
    CANCELLED = auto()

@dataclass
class ProgressEvent:
    """
    Represents a single progress event
    """
    timestamp: datetime = field(default_factory=datetime.now)
    status: ProgressStatus = ProgressStatus.PENDING
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProgressTracker:
    """
    Comprehensive progress tracking system
    """
    task_id: str
    total_steps: int
    current_step: int = 0
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    events: List[ProgressEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """
        Initialize tracker with initial setup
        """
        if not self.start_time:
            self.start_time = datetime.now()
        self.add_event(ProgressStatus.PENDING, "Task initialized")

    def add_event(
        self, 
        status: ProgressStatus, 
        message: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a progress event to the tracker

        Args:
            status (ProgressStatus): Current status
            message (Optional[str]): Event message
            metadata (Optional[Dict[str, Any]]): Additional metadata
        """
        event = ProgressEvent(
            status=status,
            message=message,
            metadata=metadata or {}
        )
        self.events.append(event)
        self.status = status

        # Update task completion times
        if status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED]:
            self.end_time = datetime.now()

    def update_progress(self, current_step: int, message: Optional[str] = None):
        """
        Update current progress step

        Args:
            current_step (int): Current progress step
            message (Optional[str]): Progress message
        """
        self.current_step = min(current_step, self.total_steps)
        self.status = ProgressStatus.RUNNING
        
        if message:
            self.add_event(ProgressStatus.RUNNING, message)

    @property
    def progress_percentage(self) -> float:
        """
        Calculate progress percentage

        Returns:
            float: Progress percentage
        """
        return (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0

    @property
    def elapsed_time(self) -> timedelta:
        """
        Calculate elapsed time

        Returns:
            timedelta: Time elapsed since task start
        """
        return datetime.now() - self.start_time if self.start_time else timedelta()

    @property
    def estimated_time_remaining(self) -> Optional[timedelta]:
        """
        Estimate time remaining for the task

        Returns:
            Optional[timedelta]: Estimated time remaining
        """
        if self.current_step == 0 or self.total_steps == 0:
            return None

        elapsed = self.elapsed_time.total_seconds()
        estimated_total_time = (elapsed / self.current_step) * self.total_steps
        return timedelta(seconds=max(0, estimated_total_time - elapsed))

class ProgressTrackerManager:
    """
    Advanced progress tracker management system
    """

    def __init__(
        self, 
        persistence_path: Optional[str] = None,
        auto_save_interval: int = 60
    ):
        """
        Initialize progress tracker manager

        Args:
            persistence_path (Optional[str]): Path to save progress
            auto_save_interval (int): Auto-save interval in seconds
        """
        self.trackers: Dict[str, ProgressTracker] = {}
        self.persistence_path = persistence_path
        self.auto_save_interval = auto_save_interval
        self._save_lock = asyncio.Lock()
        self._last_save_time = 0

    async def create_tracker(
        self, 
        task_id: Optional[str] = None, 
        total_steps: int = 100,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProgressTracker:
        """
        Create a new progress tracker

        Args:
            task_id (Optional[str]): Unique task identifier
            total_steps (int): Total number of steps
            metadata (Optional[Dict[str, Any]]): Additional metadata

        Returns:
            ProgressTracker: Created tracker
        """
        task_id = task_id or str(time.time())
        tracker = ProgressTracker(
            task_id=task_id, 
            total_steps=total_steps,
            metadata=metadata or {}
        )
        self.trackers[task_id] = tracker
        await self._save_tracker(tracker)
        return tracker

    async def update_tracker(
        self, 
        task_id: str, 
        current_step: int, 
        message: Optional[str] = None
    ):
        """
        Update an existing tracker

        Args:
            task_id (str): Task identifier
            current_step (int): Current progress step
            message (Optional[str]): Progress message
        """
        if task_id not in self.trackers:
            raise ValueError(f"No tracker found for task ID: {task_id}")

        tracker = self.trackers[task_id]
        tracker.update_progress(current_step, message)
        
        # Auto-save with interval
        current_time = time.time()
        if current_time - self._last_save_time >= self.auto_save_interval:
            await self._save_tracker(tracker)
            self._last_save_time = current_time

    async def _save_tracker(self, tracker: ProgressTracker):
        """
        Save tracker state to persistence storage

        Args:
            tracker (ProgressTracker): Tracker to save
        """
        if not self.persistence_path:
            return

        async with self._save_lock:
            try:
                async with aiofiles.open(self.persistence_path, mode='w') as f:
                    tracker_data = {
                        tracker.task_id: asdict(tracker)
                    }
                    await f.write(json.dumps(tracker_data, default=str))
            except Exception as e:
                print(f"Error saving tracker: {e}")

def progress_decorator(
    total_steps: Optional[int] = None,
    track_progress: bool = True
):
    """
    Decorator for tracking function progress

    Args:
        total_steps (Optional[int]): Total number of steps
        track_progress (bool): Whether to track progress

    Returns:
        Callable: Decorated function
    """
    def decorator(func: Union[Callable, Coroutine]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not track_progress:
                return await func(*args, **kwargs)

            # Create progress tracker
            tracker_manager = ProgressTrackerManager()
            tracker = await tracker_manager.create_tracker(
                total_steps=total_steps or 100
            )

            try:
                # Wrap function with progress tracking
                for step in range(total_steps or 100):
                    await tracker_manager.update_tracker(tracker.task_id, step + 1, f"Step {step + 1} of {total_steps or 100}")
                    await asyncio.sleep(0.1)  # Simulate work being done
                tracker.add_event(ProgressStatus.COMPLETED, "Task completed successfully")
            except Exception as e:
                tracker.add_event(ProgressStatus.FAILED, str(e))
                raise
            finally:
                await tracker_manager._save_tracker(tracker)

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Public API
__all__ = [
    'ProgressTracker',
    'ProgressTrackerManager',
    'ProgressStatus',
    'progress_decorator'
      ]
