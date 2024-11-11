"""
Advanced Rate Limiting Utility

Provides sophisticated rate limiting mechanisms 
for protecting resources and preventing abuse.
"""

from __future__ import annotations

import asyncio
import time
from typing import (
    Dict, 
    Any, 
    Callable, 
    Coroutine, 
    Optional, 
    Union
)
from datetime import datetime, timedelta

class RateLimiter:
    """
    Advanced rate limiting implementation with multiple strategies
    """

    def __init__(
        self, 
        max_calls: int = 10,
        period: Union[float, timedelta] = timedelta(minutes=1),
        strategy: str = 'sliding_window',
        burst_mode: bool = True
    ):
        """
        Initialize rate limiter

        Args:
            max_calls (int): Maximum number of calls allowed
            period (Union[float, timedelta]): Time period for rate limit
            strategy (str): Rate limiting strategy
            burst_mode (bool): Allow burst of requests
        """
        self.max_calls = max_calls
        self.period = period.total_seconds() if isinstance(period, timedelta) else period
        self.strategy = strategy
        self.burst_mode = burst_mode

        # Storage for tracking requests
        self._request_timestamps: Dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, key: str = 'default') -> bool:
        """
        Attempt to acquire a rate limit token

        Args:
            key (str): Unique identifier for rate limit tracking

        Returns:
            bool: Whether the request is allowed
        """
        async with self._lock:
            current_time = time.time()
            
            # Remove outdated timestamps
            if key in self._request_timestamps:
                self._request_timestamps[key] = [
                    ts for ts in self._request_timestamps[key] 
                    if current_time - ts <= self.period
                ]

            # Check rate limit based on strategy
            if self.strategy == 'fixed_window':
                return self._fixed_window_check(key, current_time)
            elif self.strategy == 'sliding_window':
                return self._sliding_window_check(key, current_time)
            elif self.strategy == 'leaky_bucket':
                return self._leaky_bucket_check(key, current_time)
            else:
                raise ValueError(f"Unknown rate limit strategy: {self.strategy}")

    def _fixed_window_check(self, key: str, current_time: float) -> bool:
        """
        Fixed window rate limiting strategy

        Args:
            key (str): Rate limit key
            current_time (float): Current timestamp

        Returns:
            bool: Whether the request is allowed
        """
        window_start = current_time - (current_time % self.period)
        window_requests = [
            ts for ts in self._request_timestamps.get(key, []) 
            if ts >= window_start
        ]

        if len(window_requests) < self.max_calls:
            self._request_timestamps.setdefault(key, []).append(current_time)
            return True
        return False

    def _sliding_window_check(self, key: str, current_time: float) -> bool:
        """
        Sliding window rate limiting strategy

        Args:
            key (str): Rate limit key
            current_time (float): Current timestamp

        Returns:
            bool: Whether the request is allowed
        """
        window_requests = [
            ts for ts in self._request_timestamps.get(key, []) 
            if current_time - ts <= self.period
        ]

        if len(window_requests) < self.max_calls:
            self._request_timestamps.setdefault(key, []).append(current_time)
            return True
        return False

    def _leaky_bucket_check(self, key: str, current_time: float) -> bool:
        """
        Leaky bucket rate limiting strategy

        Args:
            key (str): Rate limit key
            current_time (float): Current timestamp

        Returns:
            bool: Whether the request is allowed
        """
        window_requests = [
            ts for ts in self._request_timestamps.get(key, []) 
            if current_time - ts <= self.period
        ]

        if len(window_requests) < self.max_calls:
            # Additional burst mode handling
            if self.burst_mode and len(window_requests) >= self.max_calls * 0.8:
                # Allow limited additional requests with exponential backoff
                extra_allowed = max(1, int(self.max_calls * 0.2))
                if len(window_requests) < self.max_calls + extra_allowed:
                    self._request_timestamps.setdefault(key, []).append(current_time)
                    return True
            else:
                self._request_timestamps.setdefault(key, []).append(current_time)
                return True
        return False

def rate_limit(
    max_calls: int = 10,
    period: Union[float, timedelta] = timedelta(minutes=1),
    strategy: str = 'sliding_window',
    burst_mode: bool = True,
    error_message: Optional[str] = None
) -> Callable:
    """
    Rate limiting decorator for functions

    Args:
        max_calls (int): Maximum number of calls allowed
        period (Union[float, timedelta]): Time period for rate limit
        strategy (str): Rate limiting strategy
        burst_mode (bool): Allow burst of requests
        error_message (Optional[str]): Custom error message

    Returns:
        Callable: Decorated function
    """
    rate_limiter = RateLimiter(
        max_calls=max_calls, 
        period=period, 
        strategy=strategy,
        burst_mode=burst_mode
    )

    def decorator(func: Union[Callable, Coroutine]) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Use first argument as key if possible
            key = str(args[0]) if args else 'default'

            # Check rate limit
            if not await rate_limiter.acquire(key):
                raise RateLimitExceededError(
                    error_message or f"Rate limit exceeded: {max_calls} calls per {period}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

class RateLimitExceededError(Exception):
    """
    Custom exception for rate limit violations
    """
    pass

class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that dynamically adjusts limits
    """

    def __init__(
        self, 
        initial_max_calls: int = 10,
        min_max_calls: int = 5,
        max_max_calls: int = 50,
        adjustment_factor: float = 0.1
    ):
        """
        Initialize adaptive rate limiter

        Args:
            initial_max_calls (int): Initial maximum calls
            min_max_calls (int): Minimum limit for calls
            max_max_calls (int): Maximum limit for calls
            adjustment_factor (float): Factor for dynamic adjustment
        """
        super().__init__(max_calls=initial_max_calls)
        self.initial_max_calls = initial_max_calls
        self.min_max_calls = min_max_calls
        self.max_max_calls = max_max_calls
        self.adjustment_factor = adjustment_factor
        
        # Tracking for adaptive adjustment
        self._success_count: Dict[str, int] = {}
        self._failure_count: Dict[str, int] = {}

    async def acquire(self, key: str = 'default') -> bool:
        """
        Acquire rate limit with adaptive adjustment

        Args:
            key (str): Unique identifier for rate limit tracking

        Returns:
            bool: Whether the request is allowed
        """
        is_allowed = await super().acquire(key)
        
        # Track success and failure
        if is_allowed:
            self._success_count[key] = self._success_count.get(key, 0) + 1
        else:
            self ._failure_count[key] = self._failure_count.get(key, 0) + 1

        # Adjust limits based on success and failure rates
        self._adjust_limits(key)

        return is_allowed

    def _adjust_limits(self, key: str):
        """
        Adjust rate limits based on success and failure counts

        Args:
            key (str): Rate limit key
        """
        success_count = self._success_count.get(key, 0)
        failure_count = self._failure_count.get(key, 0)

        if success_count + failure_count > 0:
            success_rate = success_count / (success_count + failure_count)

            # Increase limit if success rate is high
            if success_rate > 0.8 and self.max_calls < self.max_max_calls:
                self.max_calls = min(self.max_calls + 1, self.max_max_calls)
            # Decrease limit if success rate is low
            elif success_rate < 0.5 and self.max_calls > self.min_max_calls:
                self.max_calls = max(self.max_calls - 1, self.min_max_calls)

        # Reset counts after adjustment
        self._success_count[key] = 0
        self._failure_count[key] = 0

# Public API
__all__ = [
    'RateLimiter',
    'rate_limit',
    'RateLimitExceededError',
    'AdaptiveRateLimiter'
          ]
