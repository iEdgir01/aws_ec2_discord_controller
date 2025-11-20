"""Caching service for EC2 state and API responses

Implements in-memory caching with TTL to reduce AWS API calls.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    """Cache entry with TTL"""
    value: Any
    expires_at: datetime
    hits: int = 0


class CacheService:
    """In-memory cache with TTL support"""

    def __init__(self, default_ttl_seconds: int = 30):
        """Initialize cache service

        Args:
            default_ttl_seconds: Default TTL for cache entries
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl_seconds
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            entry = self._cache.get(key)

            if not entry:
                self._stats["misses"] += 1
                return None

            if datetime.now() > entry.expires_at:
                # Expired
                del self._cache[key]
                self._stats["evictions"] += 1
                self._stats["misses"] += 1
                return None

            entry.hits += 1
            self._stats["hits"] += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds (uses default if not specified)
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)

        async with self._lock:
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    async def delete(self, key: str):
        """Delete entry from cache

        Args:
            key: Cache key
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            self._stats["evictions"] += len(self._cache)

    async def cleanup_expired(self):
        """Remove all expired entries"""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry.expires_at
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats["evictions"] += 1

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics

        Returns:
            Dict with cache stats
        """
        async with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests if total_requests > 0 else 0
            )

            return {
                **self._stats,
                "total_requests": total_requests,
                "hit_rate": hit_rate,
                "current_entries": len(self._cache)
            }

    async def get_or_set(self, key: str, factory_func, ttl_seconds: Optional[int] = None) -> Any:
        """Get value from cache or set it using factory function

        Args:
            key: Cache key
            factory_func: Async function to call if cache miss
            ttl_seconds: TTL in seconds

        Returns:
            Cached or computed value
        """
        value = await self.get(key)

        if value is not None:
            return value

        # Cache miss - compute value
        value = await factory_func()
        await self.set(key, value, ttl_seconds)
        return value


# Global cache instance
_cache_instance: Optional[CacheService] = None


def get_cache() -> CacheService:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService(default_ttl_seconds=30)
    return _cache_instance
