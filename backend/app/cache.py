"""Redis cache layer for the drug discovery platform.

This module provides a caching interface for external API responses and
computed results to reduce latency and API calls.
"""

import json
import logging
from typing import Any, Optional
import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from config.settings import settings


logger = logging.getLogger(__name__)


class CacheLayer:
    """Redis-based cache layer with TTL support and graceful error handling.
    
    Provides get(), set(), and invalidate() methods for caching data.
    Handles Redis connection errors gracefully to ensure the application
    continues functioning even when Redis is unavailable.
    """
    
    def __init__(self, redis_url: Optional[str] = None, ttl: Optional[int] = None):
        """Initialize cache layer with Redis connection.
        
        Args:
            redis_url: Redis connection URL (defaults to settings.redis_url)
            ttl: Default TTL in seconds (defaults to settings.cache_ttl)
        """
        self.redis_url = redis_url or settings.redis_url
        self.default_ttl = ttl or settings.cache_ttl
        self._client: Optional[redis.Redis] = None
        self._connected = False
    
    def _sanitize_key(self, key: str) -> str:
        """Sanitize cache key to ensure valid UTF-8 encoding.
        
        Removes or replaces invalid Unicode characters (like lone surrogates)
        that cannot be encoded in UTF-8.
        
        Args:
            key: Original cache key
            
        Returns:
            Sanitized key safe for UTF-8 encoding
        """
        try:
            # Try to encode as UTF-8, replacing invalid characters
            sanitized = key.encode('utf-8', errors='replace').decode('utf-8')
            return sanitized
        except Exception as e:
            # Fallback: use a hash of the original key
            logger.warning(f"Key sanitization failed for '{key}': {e}. Using hash.")
            return f"sanitized_{hash(key)}"
    
    async def _get_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client with connection handling.
        
        Returns:
            Redis client if connection successful, None otherwise
        """
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test connection
                await self._client.ping()
                self._connected = True
                logger.info("Redis connection established")
            except (ConnectionError, TimeoutError, RedisError) as e:
                logger.warning(f"Redis connection failed: {e}. Cache will be disabled.")
                self._connected = False
                self._client = None
                return None
        
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value (deserialized from JSON) or None if not found or error
        """
        client = await self._get_client()
        if client is None:
            return None
        
        # Sanitize key to handle invalid Unicode
        sanitized_key = self._sanitize_key(key)
        
        try:
            value = await client.get(sanitized_key)
            if value is None:
                logger.debug(f"Cache miss: {sanitized_key}")
                return None
            
            logger.debug(f"Cache hit: {sanitized_key}")
            return json.loads(value)
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for key '{sanitized_key}': {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be serialized to JSON)
            ttl: Time-to-live in seconds (defaults to self.default_ttl)
            
        Returns:
            True if successful, False otherwise
        """
        client = await self._get_client()
        if client is None:
            return False
        
        # Sanitize key to handle invalid Unicode
        sanitized_key = self._sanitize_key(key)
        ttl = ttl if ttl is not None else self.default_ttl
        
        try:
            serialized = json.dumps(value)
            await client.setex(sanitized_key, ttl, serialized)
            logger.debug(f"Cache set: {sanitized_key} (TTL: {ttl}s)")
            return True
        except (RedisError, TypeError, json.JSONEncodeError) as e:
            logger.warning(f"Cache set error for key '{sanitized_key}': {e}")
            return False
    
    async def invalidate(self, pattern: str) -> int:
        """Clear cache entries matching pattern.
        
        Args:
            pattern: Redis key pattern (supports wildcards like 'prefix:*')
            
        Returns:
            Number of keys deleted, or 0 if error
        """
        client = await self._get_client()
        if client is None:
            return 0
        
        try:
            # Find all keys matching pattern
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            if not keys:
                logger.debug(f"No keys found matching pattern: {pattern}")
                return 0
            
            # Delete all matching keys
            deleted = await client.delete(*keys)
            logger.info(f"Cache invalidated: {deleted} keys matching '{pattern}'")
            return deleted
        except RedisError as e:
            logger.warning(f"Cache invalidate error for pattern '{pattern}': {e}")
            return 0
    
    async def close(self):
        """Close Redis connection."""
        if self._client is not None:
            try:
                await self._client.close()
                logger.info("Redis connection closed")
            except RedisError as e:
                logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self._client = None
                self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected


# Global cache instance
cache = CacheLayer()
