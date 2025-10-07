#!/usr/bin/env python3
"""
Minimal test server to verify basic functionality.
"""

import os
import asyncio
from aiohttp import web

async def health_check(request):
    return web.json_response({
        "status": "healthy",
        "message": "Minimal test server is running",
        "port": os.environ.get("PORT", "8080"),
        "env_vars": {
            "PORT": os.environ.get("PORT"),
            "TG_WEBHOOK_PORT": os.environ.get("TG_WEBHOOK_PORT"),
            "TG_WEBHOOK_URL": os.environ.get("TG_WEBHOOK_URL", "not_set")[:20] + "..." if os.environ.get("TG_WEBHOOK_URL") else "not_set"
        }
    })

async def ready_check(request):
    return web.json_response({
        "status": "ready",
        "message": "Test server ready"
    })

async def main():
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/ready", ready_check)
    
    # Use Railway's PORT env var if available, otherwise default to 8080
    port = int(os.environ.get("PORT", os.environ.get("TG_WEBHOOK_PORT", "8080")))
    
    print(f"Starting minimal test server on port {port}")
    print(f"Environment variables:")
    print(f"  PORT: {os.environ.get('PORT')}")
    print(f"  TG_WEBHOOK_PORT: {os.environ.get('TG_WEBHOOK_PORT')}")
    print(f"  TG_WEBHOOK_URL: {os.environ.get('TG_WEBHOOK_URL', 'not_set')}")
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    print(f"✅ Test server started on 0.0.0.0:{port}")
    print(f"Health endpoints:")
    print(f"  - /ready")
    print(f"  - /health")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        await site.stop()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
