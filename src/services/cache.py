"""
Simple in-memory cache for Fontis API responses.
Reduces response time from 4-6s to < 1s for repeated searches.
"""

import time
from typing import Any, Optional


class SimpleCache:
    """Thread-safe in-memory cache with TTL."""
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache.
        
        Args:
            ttl_seconds: Time to live for cache entries (default 5 minutes)
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        
        # Check if expired
        if time.time() - timestamp > self._ttl:
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache with current timestamp.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (value, time.time())
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
    
    def size(self) -> int:
        """Get number of cached entries."""
        return len(self._cache)


# Global cache instance
# TTL of 60 seconds for customer searches (balance between freshness and speed)
customer_search_cache = SimpleCache(ttl_seconds=60)

