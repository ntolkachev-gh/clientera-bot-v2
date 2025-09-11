#!/usr/bin/env python3
"""
Connection pool for OpenAI Realtime API to handle multiple concurrent users.
"""

import asyncio
import random
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from ..config.env import get_settings
from ..integrations.yclients_adapter import YClientsAdapter
from ..utils.logger import get_logger
from .client import OpenAIRealtimeClient
from .events import StreamController, StreamState

logger = get_logger(__name__)
settings = get_settings()


class LoadBalancingStrategy(Enum):
    """Load balancing strategies for connection pool."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    STICKY = "sticky"  # User always gets the same connection


class ConnectionStatus:
    """Status of a single connection in the pool."""
    
    def __init__(self, connection_id: int, client: OpenAIRealtimeClient):
        self.connection_id = connection_id
        self.client = client
        self.active_users: Set[int] = set()
        self.total_requests = 0
        self.total_errors = 0
        self.created_at = datetime.utcnow()
        self.last_used = datetime.utcnow()
        self.is_healthy = True
        
    @property
    def active_count(self) -> int:
        """Number of active users on this connection."""
        return len(self.active_users)
    
    @property
    def is_available(self) -> bool:
        """Check if connection is available for new users."""
        return self.is_healthy and self.client.is_connected
    
    def update_stats(self, success: bool = True):
        """Update connection statistics."""
        self.total_requests += 1
        if not success:
            self.total_errors += 1
        self.last_used = datetime.utcnow()
    
    def get_stats(self) -> Dict:
        """Get connection statistics."""
        uptime = (datetime.utcnow() - self.created_at).total_seconds()
        return {
            "connection_id": self.connection_id,
            "active_users": self.active_count,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": self.total_errors / max(1, self.total_requests),
            "uptime_seconds": uptime,
            "last_used": self.last_used.isoformat(),
            "is_healthy": self.is_healthy,
            "is_connected": self.client.is_connected,
        }


class RealtimeConnectionPool:
    """
    Connection pool for managing multiple OpenAI Realtime API connections.
    Allows handling multiple concurrent users without conflicts.
    """
    
    def __init__(
        self,
        yclients_adapter: YClientsAdapter,
        pool_size: int = 3,
        max_users_per_connection: int = 20,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_CONNECTIONS,
    ):
        """
        Initialize connection pool.
        
        Args:
            yclients_adapter: YClients adapter for function calls
            pool_size: Number of connections in the pool
            max_users_per_connection: Maximum concurrent users per connection
            strategy: Load balancing strategy
        """
        self.yclients_adapter = yclients_adapter
        self.pool_size = min(pool_size, 10)  # Cap at 10 connections
        self.max_users_per_connection = max_users_per_connection
        self.strategy = strategy
        
        self.connections: List[ConnectionStatus] = []
        self.user_connections: Dict[int, ConnectionStatus] = {}  # user_id -> connection
        self.round_robin_index = 0
        self._lock = asyncio.Lock()
        self._initialization_task: Optional[asyncio.Task] = None
        
        logger.info(f"🏊 Initializing connection pool with {pool_size} connections")
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._initialization_task and not self._initialization_task.done():
            await self._initialization_task
            return
        
        self._initialization_task = asyncio.create_task(self._initialize_connections())
        await self._initialization_task
    
    async def _initialize_connections(self) -> None:
        """Initialize all connections in the pool."""
        logger.info(f"🔄 Creating {self.pool_size} connections...")
        
        tasks = []
        for i in range(self.pool_size):
            tasks.append(self._create_connection(i))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if not isinstance(r, Exception))
        if successful == 0:
            raise RuntimeError("Failed to create any connections in the pool")
        
        logger.info(f"Connection pool initialized with {successful}/{self.pool_size} connections")
    
    async def _create_connection(self, connection_id: int) -> ConnectionStatus:
        """Create a single connection."""
        try:
            logger.info(f"Creating connection #{connection_id}")
            client = OpenAIRealtimeClient(self.yclients_adapter)
            await client.connect()
            
            status = ConnectionStatus(connection_id, client)
            self.connections.append(status)
            
            logger.info(f"Connection #{connection_id} created successfully")
            return status
            
        except Exception as e:
            logger.error(f"Failed to create connection #{connection_id}: {e}")
            raise
    
    async def get_connection_for_user(self, user_id: int) -> Tuple[OpenAIRealtimeClient, int]:
        """
        Get a connection for a specific user.
        
        Returns:
            Tuple of (client, connection_id)
        """
        async with self._lock:
            # Check if user already has a connection (sticky sessions)
            if user_id in self.user_connections:
                conn = self.user_connections[user_id]
                if conn.is_available:
                    logger.debug(f"User {user_id} reusing connection #{conn.connection_id}")
                    return conn.client, conn.connection_id
                else:
                    # Remove stale connection mapping
                    del self.user_connections[user_id]
            
            # Select connection based on strategy
            connection = await self._select_connection()
            if not connection:
                # Try to create a new connection if pool not full
                if len(self.connections) < self.pool_size:
                    connection = await self._create_connection(len(self.connections))
                else:
                    raise RuntimeError("No available connections in pool")
            
            # Assign user to connection
            connection.active_users.add(user_id)
            self.user_connections[user_id] = connection
            connection.update_stats()
            
            logger.info(f"User {user_id} assigned to connection #{connection.connection_id} "
                       f"(active: {connection.active_count}/{self.max_users_per_connection})")
            
            return connection.client, connection.connection_id
    
    async def _select_connection(self) -> Optional[ConnectionStatus]:
        """Select a connection based on the configured strategy."""
        available = [c for c in self.connections 
                    if c.is_available and c.active_count < self.max_users_per_connection]
        
        if not available:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            # Round-robin selection
            selected = available[self.round_robin_index % len(available)]
            self.round_robin_index += 1
            
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            # Select connection with least active users
            selected = min(available, key=lambda c: c.active_count)
            
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            # Random selection
            selected = random.choice(available)
            
        else:  # STICKY - handled in get_connection_for_user
            selected = available[0]
        
        return selected
    
    async def release_user_connection(self, user_id: int) -> None:
        """Release a user's connection when they're done."""
        async with self._lock:
            if user_id in self.user_connections:
                conn = self.user_connections[user_id]
                conn.active_users.discard(user_id)
                del self.user_connections[user_id]
                
                logger.info(f"👋 User {user_id} released from connection #{conn.connection_id} "
                           f"(active: {conn.active_count}/{self.max_users_per_connection})")
    
    async def send_user_message(
        self,
        user_id: int,
        text: str,
        message_id: Optional[int] = None
    ) -> Tuple[StreamController, int]:
        """
        Send a user message through the pool.
        
        Returns:
            Tuple of (StreamController, connection_id)
        """
        client, connection_id = await self.get_connection_for_user(user_id)
        
        try:
            stream = await client.send_user_message(user_id, text, message_id)
            return stream, connection_id
            
        except Exception as e:
            # Mark connection as unhealthy if it fails
            conn = self.user_connections.get(user_id)
            if conn:
                conn.update_stats(success=False)
                if conn.total_errors > 5:  # Too many errors
                    conn.is_healthy = False
                    logger.warning(f"⚠️ Connection #{conn.connection_id} marked as unhealthy")
            raise
    
    async def cancel_user_stream(self, user_id: int) -> None:
        """Cancel a user's active stream."""
        if user_id in self.user_connections:
            conn = self.user_connections[user_id]
            await conn.client.cancel_stream(user_id)
    
    def get_user_stream_state(self, user_id: int) -> Optional[StreamState]:
        """Get stream state for a user."""
        if user_id in self.user_connections:
            conn = self.user_connections[user_id]
            return conn.client.get_stream_state(user_id)
        return None
    
    async def health_check(self) -> None:
        """Perform health check on all connections."""
        logger.info("🏥 Performing health check on connection pool")
        
        for conn in self.connections:
            try:
                # Check if connection is still alive
                if not conn.client.is_connected:
                    logger.warning(f" Connection #{conn.connection_id} is disconnected")
                    conn.is_healthy = False
                    
                    # Try to reconnect
                    await conn.client.connect()
                    conn.is_healthy = True
                    logger.info(f"Connection #{conn.connection_id} reconnected")
                    
            except Exception as e:
                logger.error(f" Health check failed for connection #{conn.connection_id}: {e}")
                conn.is_healthy = False
    
    def get_pool_stats(self) -> Dict:
        """Get comprehensive pool statistics."""
        total_active = sum(c.active_count for c in self.connections)
        total_requests = sum(c.total_requests for c in self.connections)
        total_errors = sum(c.total_errors for c in self.connections)
        
        return {
            "pool_size": len(self.connections),
            "configured_size": self.pool_size,
            "total_active_users": total_active,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": total_errors / max(1, total_requests),
            "strategy": self.strategy.value,
            "max_users_per_connection": self.max_users_per_connection,
            "connections": [c.get_stats() for c in self.connections],
            "healthy_connections": sum(1 for c in self.connections if c.is_healthy),
            "user_distribution": {
                f"connection_{c.connection_id}": c.active_count 
                for c in self.connections
            }
        }
    
    async def cleanup(self) -> None:
        """Clean up all connections in the pool."""
        logger.info("🧹 Cleaning up connection pool")
        
        # Release all users
        self.user_connections.clear()
        
        # Disconnect all connections
        tasks = []
        for conn in self.connections:
            conn.active_users.clear()
            tasks.append(conn.client.disconnect())
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.connections.clear()
        logger.info("✅ Connection pool cleaned up")


# Global pool instance
_connection_pool: Optional[RealtimeConnectionPool] = None


async def get_connection_pool(
    yclients_adapter: YClientsAdapter,
    pool_size: int = None
) -> RealtimeConnectionPool:
    """Get or create global connection pool instance."""
    global _connection_pool
    
    if _connection_pool is None:
        # Get pool size from environment or use default
        if pool_size is None:
            pool_size = int(settings.WS_POOL_SIZE) if hasattr(settings, 'WS_POOL_SIZE') else 3
        
        _connection_pool = RealtimeConnectionPool(
            yclients_adapter=yclients_adapter,
            pool_size=pool_size,
            max_users_per_connection=20,
            strategy=LoadBalancingStrategy.LEAST_CONNECTIONS
        )
        await _connection_pool.initialize()
    
    return _connection_pool


async def cleanup_connection_pool() -> None:
    """Cleanup global connection pool."""
    global _connection_pool
    
    if _connection_pool:
        await _connection_pool.cleanup()
        _connection_pool = None

