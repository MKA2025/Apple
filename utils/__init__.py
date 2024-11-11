"""
Utility Module Initialization

Provides core utility functions, decorators, 
and helper classes for the application.
"""

from __future__ import annotations

import os
import re
import uuid
import hashlib
import logging
from typing import (
    Any, 
    Callable, 
    TypeVar, 
    Generic, 
    Optional, 
    Union, 
    Dict
)
from functools import wraps, lru_cache
from datetime import datetime, timedelta

# Type variable for generic decorators
T = TypeVar('T')

class SingletonMeta(type):
    """
    Metaclass for implementing Singleton design pattern
    
    Ensures only one instance of a class is created
    """
    _instances: Dict[type, Any] = {}

    def __call__(cls, *args, **kwargs):
        """
        Create or return existing instance
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Instance of the class
        """
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

def retry(
    max_attempts: int = 3, 
    delay: float = 1.0, 
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Retry decorator for handling function failures
    
    Args:
        max_attempts (int): Maximum number of retry attempts
        delay (float): Initial delay between retries
        backoff (float): Exponential backoff factor
        exceptions (tuple): Exceptions to catch and retry
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt == max_attempts:
                        raise
                    
                    # Log retry attempt
                    logging.warning(
                        f"Retry attempt {attempt} for {func.__name__}: {str(e)}"
                    )
                    
                    # Wait with exponential backoff
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        
        return wrapper
    return decorator

def validate_apple_music_url(url: str) -> bool:
    """
    Validate Apple Music URL format
    
    Args:
        url (str): URL to validate
    
    Returns:
        bool: Whether the URL is a valid Apple Music URL
    """
    apple_music_pattern = r'^https?://(?:music\.)?apple\.com/([a-z]{2})/(?:album|playlist|artist|song|music-video)/[^/]+/?\d*'
    return bool(re.match(apple_music_pattern, url, re.IGNORECASE))

def generate_unique_id() -> str:
    """
    Generate a unique identifier
    
    Returns:
        str: Unique identifier
    """
    return str(uuid.uuid4())

def generate_hash(data: Any) -> str:
    """
    Generate a consistent hash for given data
    
    Args:
        data (Any): Data to hash
    
    Returns:
        str: Hash of the data
    """
    # Convert data to a consistent string representation
    data_str = str(data)
    return hashlib.md5(data_str.encode()).hexdigest()

class CachedProperty:
    """
    Descriptor for cached property implementation
    
    Caches the result of a method after first call
    """
    def __init__(self, func: Callable):
        """
        Initialize cached property
        
        Args:
            func (Callable): Method to cache
        """
        self.func = func
        self.name = func.__name__
        self.__doc__ = func.__doc__
    
    def __get__(self, instance, owner=None):
        """
        Get cached value or compute and cache
        
        Args:
            instance: Instance of the class
            owner: Owner class
        
        Returns:
            Cached or computed value
        """
        if instance is None:
            return self
        
        value = instance.__dict__[self.name] = self.func(instance)
        return value

def rate_limit(
    max_calls: int, 
    period: timedelta
) -> Callable:
    """
    Rate limiting decorator
    
    Args:
        max_calls (int): Maximum number of calls
        period (timedelta): Time period for rate limit
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        calls = []
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = datetime.now()
            
            # Remove expired calls
            calls[:] = [call for call in calls if now - call < period]
            
            if len(calls) >= max_calls:
                raise RuntimeError("Rate limit exceeded")
            
            calls.append(now)
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing or replacing invalid characters
    
    Args:
        filename (str): Original filename
    
    Returns:
        str: Sanitized filename
    """
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit filename length
    max_length = 255
    filename = filename[:max_length]
    
    return filename.strip()

class LazyProperty:
    """
    Lazy property descriptor
    
    Computes value only when first accessed
    """
    def __init__(self, func: Callable):
        """
        Initialize lazy property
        
        Args:
            func (Callable): Method to lazily compute
        """
        self.func = func
        self.name = func.__name__
        self.__doc__ = func.__doc__
    
    def __get__(self, instance, owner=None):
        """
        Compute and cache value on first access
        
        Args:
            instance: Instance of the class
            owner: Owner class
        
        Returns:
            Computed value
        """
        if instance is None:
            return self
        
        value = self.func(instance)
        setattr(instance, self.name, value)
        return value

# Public API
__all__ = [
    'SingletonMeta',
    'retry',
    'validate_apple_music_url',
    'generate_unique_id',
    'generate_hash',
    'CachedProperty',
    'rate_limit',
    'safe_filename',
    'LazyProperty'
]
