"""
Simple TTL cache for data.
"""

import asyncio
import time
from typing import Any, Dict, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TTLCache:
    """Simple TTL cache implementation."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())
    
    async def _cleanup_expired(self):
        """Clean up expired cache entries."""
        while True:
            try:
                current_time = time.time()
                expired_keys = []
                
                for key, entry in self._cache.items():
                    if entry['expires_at'] < current_time:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self._cache[key]
                
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                
                # Sleep for 5 minutes before next cleanup
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            entry = self._cache[key]
            if entry['expires_at'] > time.time():
                return entry['value']
            else:
                # Expired, remove it
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL in seconds."""
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }
    
    def delete(self, key: str):
        """Delete key from cache."""
        self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cache."""
        self._cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        active_entries = sum(1 for entry in self._cache.values() if entry['expires_at'] > current_time)
        
        return {
            'total_entries': len(self._cache),
            'active_entries': active_entries,
            'expired_entries': len(self._cache) - active_entries
        }


# Global cache instance
_cache: Optional[TTLCache] = None


def get_cache() -> TTLCache:
    """Get global cache instance."""
    global _cache
    if _cache is None:
        _cache = TTLCache()
    return _cache


class Cache:
    """Cache class with TTL support."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            entry = self._cache[key]
            if entry['expires_at'] > time.time():
                return entry['value']
            else:
                # Expired, remove it
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache with default TTL."""
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + self.ttl_seconds
        }
    
    def clear(self):
        """Clear all cache."""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        active_entries = sum(1 for entry in self._cache.values() if entry['expires_at'] > current_time)
        
        return {
            'total_entries': len(self._cache),
            'active_entries': active_entries,
            'expired_entries': len(self._cache) - active_entries,
            'ttl_seconds': self.ttl_seconds
        }


async def cleanup_cache():
    """Cleanup cache resources."""
    global _cache
    if _cache and _cache._cleanup_task:
        _cache._cleanup_task.cancel()
        try:
            await _cache._cleanup_task
        except asyncio.CancelledError:
            pass
    _cache = None
