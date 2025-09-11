#!/usr/bin/env python3
"""
Test script for WebSocket reconnection improvements.
"""

import asyncio
import logging
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, '../src')

from src.config.env import get_settings
from src.integrations.yclients_adapter import YClientsAdapter
from src.realtime.client import OpenAIRealtimeClient
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def test_connection_stability():
    """Test WebSocket connection stability and reconnection."""
    logger.info("🧪 Starting WebSocket reconnection test")
    
    # Create adapter and client
    adapter = YClientsAdapter()
    client = OpenAIRealtimeClient(adapter)
    
    try:
        # Initial connection
        logger.info("1️⃣ Testing initial connection...")
        await client.connect()
        
        # Print connection stats
        stats = client.get_connection_stats()
        logger.info(f"📊 Connection stats: {stats}")
        
        # Wait a bit to see if connection stays stable
        logger.info("⏳ Waiting 10 seconds to test connection stability...")
        await asyncio.sleep(10)
        
        stats = client.get_connection_stats()
        logger.info(f"📊 Connection stats after 10s: {stats}")
        
        # Test sending a message
        logger.info("2️⃣ Testing message sending...")
        stream = await client.send_user_message(
            user_id=12345,
            text="Привет! Это тест соединения.",
            message_id=1
        )
        
        # Wait for response
        logger.info("⏳ Waiting for response...")
        timeout = 30
        start_time = datetime.utcnow()
        
        while stream.state.value in ['idle', 'streaming']:
            if (datetime.utcnow() - start_time).seconds > timeout:
                logger.error(" Response timeout")
                break
            await asyncio.sleep(0.5)
        
        logger.info(f"Stream finished with state: {stream.state}")
        if hasattr(stream, 'accumulated_text') and stream.accumulated_text:
            logger.info(f"📝 Response: {stream.accumulated_text[:100]}...")
        
        # Test connection monitoring
        logger.info("3️⃣ Testing connection monitoring (waiting 30s)...")
        await asyncio.sleep(30)
        
        stats = client.get_connection_stats()
        logger.info(f"📊 Final connection stats: {stats}")
        
    except Exception as e:
        logger.error(f" Test failed: {e}")
    
    finally:
        logger.info("🧹 Cleaning up...")
        await client.disconnect()
        logger.info("✅ Test completed")


async def test_reconnection_after_disconnect():
    """Test reconnection after forced disconnection."""
    logger.info("🧪 Starting reconnection after disconnect test")
    
    adapter = YClientsAdapter()
    client = OpenAIRealtimeClient(adapter)
    
    try:
        # Connect
        await client.connect()
        logger.info("✅ Initial connection established")
        
        # Force close the websocket to simulate network issue
        if client.websocket:
            logger.info("🔌 Forcing WebSocket disconnect...")
            await client.websocket.close()
        
        # Wait for reconnection
        logger.info("⏳ Waiting for automatic reconnection...")
        await asyncio.sleep(10)
        
        stats = client.get_connection_stats()
        logger.info(f"📊 Stats after forced disconnect: {stats}")
        
        # Try to send a message (should trigger reconnection if needed)
        logger.info("📤 Testing message after reconnection...")
        await client.send_user_message(
            user_id=12346,
            text="Тест после переподключения",
            message_id=2
        )
        
        logger.info("✅ Message sent successfully after reconnection")
        
    except Exception as e:
        logger.error(f" Reconnection test failed: {e}")
    
    finally:
        await client.disconnect()


async def main():
    """Run all tests."""
    logger.info("🚀 Starting WebSocket reconnection tests")
    
    # Set log level to INFO for better visibility
    logging.getLogger().setLevel(logging.INFO)
    
    try:
        await test_connection_stability()
        await asyncio.sleep(2)  # Brief pause between tests
        await test_reconnection_after_disconnect()
        
    except KeyboardInterrupt:
        logger.info("🛑 Tests interrupted by user")
    except Exception as e:
        logger.error(f" Test suite failed: {e}")
    
    logger.info("🏁 All tests completed")


if __name__ == "__main__":
    asyncio.run(main())
