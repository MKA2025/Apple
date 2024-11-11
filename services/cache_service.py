"""
Cache Service Module

Provides advanced caching capabilities with multiple 
storage backends and cache management strategies.
"""

from __future__ import annotations

import os
import json
import time
import asyncio
import hashlib
import logging
from typing import (
    Any, 
    Optional, 
    Dict, 
    Union, 
    List, 
    Callable, 
    Coroutine
)
from pathlib import Path
from datetime import datetime, timedelta

import redis
import aioredis
import diskcache
from cachetools import TTLCache, cached
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from gamdl.models import (
    CacheConfig, 
    CacheType, 
    CacheBackend
)
from gamdl.utils import SingletonMeta

Base = declarative_base()

class CacheEntry(Base):
    """
    SQLAlchemy model for cache entries
    """
    __tablename__ = 'cache_entries'

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)
    expiration = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class CacheService(metaclass=SingletonMeta):
    """
    Advanced multi-backend caching service
    """

    def __init__(
        self, 
        config: Optional[CacheConfig] = None
    ):
        """
        Initialize cache service

        Args:
            config (Optional[CacheConfig]): Cache configuration
        """
        self.config = config or CacheConfig()
        self.logger = logging.getLogger(__name__)

        # Initialize cache backends
        self._memory_cache = self._init_memory_cache()
        self._disk_cache = self._init_disk_cache()
        self._redis_cache = self._init_redis_cache()
        self._sql_cache = self._init_sql_cache()

    def _init_memory_cache(self) -> Optional[TTLCache]:
        """
        Initialize in-memory cache

        Returns:
            Optional[TTLCache]: Memory cache instance
        """
        try:
            return TTLCache(
                maxsize=self.config.memory_cache_size, 
                ttl=self.config.default_ttl
            )
        except Exception as e:
            self.logger.error(f"Memory cache initialization failed: {e}")
            return None

    def _init_disk_cache(self) -> Optional[diskcache.Cache]:
        """
        Initialize disk-based cache

        Returns:
            Optional[diskcache.Cache]: Disk cache instance
        """
        try:
            cache_dir = Path(self.config.disk_cache_directory)
            cache_dir.mkdir(parents=True, exist_ok=True)
            return diskcache.Cache(str(cache_dir))
        except Exception as e:
            self.logger.error(f"Disk cache initialization failed: {e}")
            return None

    def _init_redis_cache(self) -> Optional[Union[redis.Redis, aioredis.Redis]]:
        """
        Initialize Redis cache

        Returns:
            Optional[Union[redis.Redis, aioredis.Redis]]: Redis cache instance
        """
        if not self.config.redis_config:
            return None

        try:
            if self.config.async_mode:
                return aioredis.from_url(
                    self.config.redis_config.url,
                    encoding="utf-8",
                    decode_responses=True
                )
            else:
                return redis.Redis.from_url(
                    self.config.redis_config.url,
                    encoding="utf-8",
                    decode_responses=True
                )
        except Exception as e:
            self.logger.error(f"Redis cache initialization failed: {e}")
            return None

    def _init_sql_cache(self) -> Optional[sessionmaker]:
        """
        Initialize SQL-based cache

        Returns:
            Optional[sessionmaker]: SQL session maker
        """
        try:
            engine = create_engine(self.config.sql_cache_url)
            Base.metadata.create_all(engine)
            return sessionmaker(bind=engine)
        except Exception as e:
            self.logger.error(f"SQL cache initialization failed: {e}")
            return None

    def _generate_cache_key(self, key: str) -> str:
        """
        Generate a standardized cache key

        Args:
            key (str): Original cache key

        Returns:
            str: Hashed cache key
        """
        return hashlib.md5(key.encode()).hexdigest()

    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        backend: Optional[CacheBackend] = None
    ):
        """
        Set a cache entry

        Args:
            key (str): Cache key
            value (Any): Cache value
            ttl (Optional[int]): Time to live in seconds
            backend (Optional[CacheBackend]): Cache backend
        """
        ttl = ttl or self.config.default_ttl
        backend = backend or self.config.default_backend
        hashed_key = self._generate_cache_key(key)

        try:
            serialized_value = json.dumps(value)

            if backend == CacheBackend.MEMORY and self._memory_cache:
                self._memory_cache[hashed_key] = serialized_value

            elif backend == CacheBackend.DISK and self._disk_cache:
                self._disk_cache.set(hashed_key, serialized_value, expire=ttl)

            elif backend == CacheBackend.REDIS and self._redis_cache:
                if self.config.async_mode:
                    await self._redis_cache.setex(hashed_key, ttl, serialized_value)
                else:
                    self._redis_cache.setex(hashed_key, ttl, serialized_value)

            elif backend == CacheBackend.SQL and self._sql_cache:
                session = self._sql_cache()
                try:
                    existing_entry = session.query(CacheEntry).filter_by(key=hashed_key).first()
                    if existing_entry:
                        existing_entry.value = serialized_value
                        existing_entry.expiration = datetime.utcnow() + timedelta(seconds=ttl)
                    else:
                        new_entry = CacheEntry(
                            key=hashed_key,
                            value=serialized_value,
                            expiration=datetime.utcnow() + timedelta(seconds=ttl)
                        )
                        session.add(new_entry)
                    session.commit()
                finally:
                    session.close()

        except Exception as e:
            self.logger.error(f"Cache set failed for key {key}: {e}")

    async def get(
        self, 
        key: str, 
        backend: Optional[CacheBackend] = None
    ) -> Optional[Any]:
        """
        Get a cache entry

        Args:
            key (str): Cache key
            backend (Optional[CacheBackend]): Cache backend

        Returns:
            Optional[Any]: Cached value
        """
        backend = backend or self.config.default_backend
        hashed_key = self._generate_cache_key(key)

        try:
            if backend == CacheBackend.MEMORY and self._memory_cache:
                value = self._memory_cache.get(hashed_key)

            elif backend == CacheBackend.DISK and self._disk_cache:
                value = self._disk_cache.get(hashed_key)

            elif backend == CacheBackend.REDIS and self._redis_cache:
                if self.config.async_mode:
                    value = await self._redis_cache.get(hashed_key)
                else:
                    value = self._redis_cache.get(hashed_key)

            elif backend == CacheBackend.SQL and self._sql_cache: session = self._sql_cache()
                try:
                    entry = session.query(CacheEntry).filter_by(key=hashed_key).first()
                    value = entry.value if entry and entry.expiration > datetime.utcnow() else None
                finally:
                    session.close()

            else:
                value = None

            return json.loads(value) if value else None

        except Exception as e:
            self.logger.error(f"Cache get failed for key {key}: {e}")
            return None

    async def delete(
        self, 
        key: str, 
        backend: Optional[CacheBackend] = None
    ):
        """
        Delete a cache entry

        Args:
            key (str): Cache key
            backend (Optional[CacheBackend]): Cache backend
        """
        backend = backend or self.config.default_backend
        hashed_key = self._generate_cache_key(key)

        try:
            if backend == CacheBackend.MEMORY and self._memory_cache:
                del self._memory_cache[hashed_key]

            elif backend == CacheBackend.DISK and self._disk_cache:
                self._disk_cache.delete(hashed_key)

            elif backend == CacheBackend.REDIS and self._redis_cache:
                if self.config.async_mode:
                    await self._redis_cache.delete(hashed_key)
                else:
                    self._redis_cache.delete(hashed_key)

            elif backend == CacheBackend.SQL and self._sql_cache:
                session = self._sql_cache()
                try:
                    entry = session.query(CacheEntry).filter_by(key=hashed_key).first()
                    if entry:
                        session.delete(entry)
                        session.commit()
                finally:
                    session.close()

        except Exception as e:
            self.logger.error(f"Cache delete failed for key {key}: {e}")

# Public API
__all__ = [
    'CacheService'
]
