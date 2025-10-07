#!/usr/bin/env python3
"""
Test script for health check endpoints.
"""

import asyncio
import aiohttp
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.env import get_settings

async def test_health_endpoints():
    """Test health check endpoints."""
    settings = get_settings()
    base_url = f"http://localhost:{settings.TG_WEBHOOK_PORT}"
    
    print(f"Testing health endpoints on {base_url}")
    
    async with aiohttp.ClientSession() as session:
        # Test /ready endpoint
        try:
            async with session.get(f"{base_url}/ready") as response:
                print(f"✅ /ready: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"   Response: {data}")
                else:
                    text = await response.text()
                    print(f"   Error: {text}")
        except Exception as e:
            print(f"❌ /ready failed: {e}")
        
        # Test /health endpoint
        try:
            async with session.get(f"{base_url}/health") as response:
                print(f"✅ /health: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"   Response: {data}")
                else:
                    text = await response.text()
                    print(f"   Error: {text}")
        except Exception as e:
            print(f"❌ /health failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_health_endpoints())
