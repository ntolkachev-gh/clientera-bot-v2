#!/usr/bin/env python3
"""
Test script for connection pool with multiple concurrent users.
"""

import asyncio
import random
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, '../src')

from src.config.env import get_settings
from src.integrations.yclients_adapter import YClientsAdapter
from src.realtime.connection_pool import get_connection_pool, LoadBalancingStrategy
from src.realtime.events import StreamState
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def simulate_user(user_id: int, message_count: int = 3):
    """Simulate a user sending messages."""
    user_name = f"User_{user_id}"
    logger.info(f"{user_name} starting simulation")
    
    adapter = YClientsAdapter()
    pool = await get_connection_pool(adapter)
    
    messages = [
        "Привет! Хочу записаться к стоматологу",
        "Какие услуги вы предоставляете?",
        "Сколько стоит лечение кариеса?",
        "Покажите свободные слоты на завтра",
        "Хочу записаться к терапевту на следующей неделе",
    ]
    
    for i in range(message_count):
        try:
            # Random delay between messages
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            message = random.choice(messages)
            logger.info(f"📤 {user_name} sending: {message[:30]}...")
            
            # Send message through pool
            stream, connection_id = await pool.send_user_message(
                user_id=user_id,
                text=message,
                message_id=i
            )
            
            logger.info(f"{user_name} assigned to connection #{connection_id}")
            
            # Wait for response (with timeout)
            timeout = 15
            start_time = datetime.utcnow()
            
            while True:
                state = pool.get_user_stream_state(user_id)
                
                if state in [StreamState.DONE, StreamState.ERROR, StreamState.CANCELLED]:
                    logger.info(f"{user_name} got response (state: {state})")
                    break
                
                if (datetime.utcnow() - start_time).seconds > timeout:
                    logger.warning(f"⏱️ {user_name} timeout waiting for response")
                    await pool.cancel_user_stream(user_id)
                    break
                
                await asyncio.sleep(0.1)
            
            # Release connection
            await pool.release_user_connection(user_id)
            
        except Exception as e:
            logger.error(f" {user_name} error: {e}")
    
    logger.info(f"👋 {user_name} finished simulation")


async def test_concurrent_users(user_count: int = 5):
    """Test multiple concurrent users."""
    logger.info(f"🧪 Testing with {user_count} concurrent users")
    
    # Initialize pool
    adapter = YClientsAdapter()
    pool = await get_connection_pool(
        adapter,
        pool_size=3  # Use 3 connections for testing
    )
    
    # Create user tasks
    tasks = []
    for i in range(1, user_count + 1):
        user_id = 1000 + i
        task = asyncio.create_task(simulate_user(user_id, message_count=2))
        tasks.append(task)
        
        # Small delay between user starts
        await asyncio.sleep(0.2)
    
    # Wait for all users to complete
    logger.info("⏳ Waiting for all users to complete...")
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Print final statistics
    stats = pool.get_pool_stats()
    logger.info("📊 Final Pool Statistics:")
    logger.info(f"  • Total requests: {stats['total_requests']}")
    logger.info(f"  • Total errors: {stats['total_errors']}")
    logger.info(f"  • Error rate: {stats['error_rate']:.1%}")
    logger.info(f"  • Healthy connections: {stats['healthy_connections']}/{stats['pool_size']}")
    
    for conn_stats in stats['connections']:
        logger.info(f"  • Connection #{conn_stats['connection_id']}: "
                   f"{conn_stats['total_requests']} requests, "
                   f"{conn_stats['total_errors']} errors")
    
    # Cleanup
    await pool.cleanup()
    logger.info("✅ Test completed successfully")


async def test_load_balancing_strategies():
    """Test different load balancing strategies."""
    logger.info("🧪 Testing load balancing strategies")
    
    adapter = YClientsAdapter()
    
    strategies = [
        LoadBalancingStrategy.ROUND_ROBIN,
        LoadBalancingStrategy.LEAST_CONNECTIONS,
        LoadBalancingStrategy.RANDOM,
    ]
    
    for strategy in strategies:
        logger.info(f"\n📋 Testing strategy: {strategy.value}")
        
        # Create pool with specific strategy
        pool = await get_connection_pool(adapter)
        pool.strategy = strategy
        
        # Simulate some users
        for i in range(6):
            user_id = 2000 + i
            client, conn_id = await pool.get_connection_for_user(user_id)
            logger.info(f"  User {user_id} -> Connection #{conn_id}")
        
        # Show distribution
        stats = pool.get_pool_stats()
        logger.info(f"  Distribution: {stats['user_distribution']}")
        
        # Cleanup
        await pool.cleanup()
        
        # Reset global pool
        from src.realtime.connection_pool import _connection_pool
        _connection_pool = None
        
        await asyncio.sleep(1)
    
    logger.info("✅ Strategy test completed")


async def test_connection_failure_recovery():
    """Test pool behavior when connections fail."""
    logger.info("🧪 Testing connection failure recovery")
    
    adapter = YClientsAdapter()
    pool = await get_connection_pool(adapter, pool_size=2)
    
    # Simulate connection failure
    logger.info("💥 Simulating connection failure...")
    if pool.connections:
        pool.connections[0].is_healthy = False
        pool.connections[0].client.is_connected = False
    
    # Perform health check
    await pool.health_check()
    
    # Check stats
    stats = pool.get_pool_stats()
    logger.info(f"📊 After health check: {stats['healthy_connections']}/{stats['pool_size']} healthy")
    
    # Try to send message (should use healthy connection)
    try:
        stream, conn_id = await pool.send_user_message(
            user_id=3000,
            text="Test after failure",
            message_id=1
        )
        logger.info(f"Message sent through connection #{conn_id}")
    except Exception as e:
        logger.error(f" Failed to send message: {e}")
    
    await pool.cleanup()
    logger.info("✅ Recovery test completed")


async def main():
    """Run all pool tests."""
    logger.info("🚀 Starting connection pool tests")
    
    try:
        # Test 1: Multiple concurrent users
        await test_concurrent_users(user_count=5)
        await asyncio.sleep(2)
        
        # Test 2: Load balancing strategies
        await test_load_balancing_strategies()
        await asyncio.sleep(2)
        
        # Test 3: Connection failure recovery
        await test_connection_failure_recovery()
        
    except KeyboardInterrupt:
        logger.info("🛑 Tests interrupted by user")
    except Exception as e:
        logger.error(f" Test suite failed: {e}")
        raise
    
    logger.info("🏁 All pool tests completed")


if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.INFO)
    
    asyncio.run(main())
