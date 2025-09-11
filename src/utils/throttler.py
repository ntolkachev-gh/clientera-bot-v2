#!/usr/bin/env python3
"""
Message throttling utility for Telegram editMessageText.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, Optional

from ..config.env import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MessageThrottler:
    """Throttle Telegram message edits to avoid rate limits."""
    
    def __init__(self, throttle_ms: int = None):
        self.throttle_ms = throttle_ms or settings.STREAM_THROTTLE_MS
        self.last_edit_times: Dict[str, datetime] = {}
        self.pending_tasks: Dict[str, asyncio.Task] = {}
        self.latest_content: Dict[str, str] = {}
    
    async def throttled_edit(
        self,
        key: str,
        content: str,
        edit_function: Callable[[str], Awaitable[Any]],
        force: bool = False
    ) -> None:
        """
        Throttle message edits to avoid rate limits.
        
        Args:
            key: Unique identifier for the message (e.g., "user_id:message_id")
            content: New message content
            edit_function: Async function to call for editing message
            force: If True, ignore throttling and edit immediately
        """
        self.latest_content[key] = content
        
        if force:
            await self._execute_edit(key, edit_function)
            return
        
        # Check if we need to throttle
        now = datetime.utcnow()
        last_edit = self.last_edit_times.get(key)
        
        if last_edit:
            time_since_last = (now - last_edit).total_seconds() * 1000
            if time_since_last < self.throttle_ms:
                # Schedule delayed edit
                await self._schedule_delayed_edit(key, edit_function)
                return
        
        # Edit immediately
        await self._execute_edit(key, edit_function)
    
    async def _execute_edit(self, key: str, edit_function: Callable[[str], Awaitable[Any]]) -> None:
        """Execute the message edit."""
        content = self.latest_content.get(key, "")
        if not content:
            return
        
        try:
            await edit_function(content)
            self.last_edit_times[key] = datetime.utcnow()
            logger.debug(f"Message edited for key: {key}")
            
        except Exception as e:
            logger.error(f"Failed to edit message for key {key}: {e}")
        
        finally:
            # Clean up pending task if exists
            if key in self.pending_tasks:
                self.pending_tasks.pop(key, None)
    
    async def _schedule_delayed_edit(self, key: str, edit_function: Callable[[str], Awaitable[Any]]) -> None:
        """Schedule a delayed edit."""
        # Cancel existing pending task
        if key in self.pending_tasks:
            self.pending_tasks[key].cancel()
        
        # Calculate delay
        last_edit = self.last_edit_times.get(key, datetime.utcnow())
        delay_ms = self.throttle_ms - (datetime.utcnow() - last_edit).total_seconds() * 1000
        delay_seconds = max(0, delay_ms / 1000)
        
        # Schedule new task
        async def delayed_edit():
            await asyncio.sleep(delay_seconds)
            await self._execute_edit(key, edit_function)
        
        self.pending_tasks[key] = asyncio.create_task(delayed_edit())
        logger.debug(f"Scheduled delayed edit for key {key} in {delay_seconds:.2f}s")
    
    def cancel_pending_edits(self, key: str) -> None:
        """Cancel any pending edits for the given key."""
        if key in self.pending_tasks:
            self.pending_tasks[key].cancel()
            self.pending_tasks.pop(key, None)
            logger.debug(f"Cancelled pending edits for key: {key}")
    
    def cleanup_old_entries(self, max_age_minutes: int = 60) -> None:
        """Clean up old entries to prevent memory leaks."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        
        # Clean up old edit times
        old_keys = [
            key for key, timestamp in self.last_edit_times.items()
            if timestamp < cutoff_time
        ]
        
        for key in old_keys:
            self.last_edit_times.pop(key, None)
            self.latest_content.pop(key, None)
            
            # Cancel and remove pending tasks
            if key in self.pending_tasks:
                self.pending_tasks[key].cancel()
                self.pending_tasks.pop(key, None)
        
        if old_keys:
            logger.debug(f"Cleaned up {len(old_keys)} old throttler entries")


# Global throttler instance
_message_throttler: Optional[MessageThrottler] = None


def get_message_throttler() -> MessageThrottler:
    """Get global message throttler instance."""
    global _message_throttler
    
    if _message_throttler is None:
        _message_throttler = MessageThrottler()
    
    return _message_throttler


class RateLimiter:
    """Simple rate limiter for user requests."""
    
    def __init__(self, max_requests: int = None, window_seconds: int = None):
        self.max_requests = max_requests or settings.RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW
        self.requests: Dict[int, list] = {}  # user_id -> list of timestamps
    
    def is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited."""
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=self.window_seconds)
        
        # Clean up old requests
        if user_id in self.requests:
            self.requests[user_id] = [
                timestamp for timestamp in self.requests[user_id]
                if timestamp > cutoff_time
            ]
        else:
            self.requests[user_id] = []
        
        # Check if rate limited
        if len(self.requests[user_id]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return True
        
        # Add current request
        self.requests[user_id].append(now)
        return False
    
    def get_remaining_requests(self, user_id: int) -> int:
        """Get remaining requests for user."""
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=self.window_seconds)
        
        if user_id not in self.requests:
            return self.max_requests
        
        # Count recent requests
        recent_requests = [
            timestamp for timestamp in self.requests[user_id]
            if timestamp > cutoff_time
        ]
        
        return max(0, self.max_requests - len(recent_requests))
    
    def cleanup_old_entries(self, max_age_minutes: int = 60) -> None:
        """Clean up old entries to prevent memory leaks."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        
        for user_id in list(self.requests.keys()):
            self.requests[user_id] = [
                timestamp for timestamp in self.requests[user_id]
                if timestamp > cutoff_time
            ]
            
            # Remove empty lists
            if not self.requests[user_id]:
                self.requests.pop(user_id, None)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    
    return _rate_limiter
