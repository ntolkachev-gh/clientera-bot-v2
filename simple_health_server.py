#!/usr/bin/env python3
"""
Simple health server for Railway deployment testing.
This is a minimal server that should work in Railway environment.
"""

import os
import asyncio
import logging
from aiohttp import web

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def health_check(request):
    """Health check endpoint."""
    return web.json_response({
        "status": "healthy",
        "message": "Simple health server is running",
        "environment": {
            "PORT": os.environ.get("PORT"),
            "RAILWAY_ENVIRONMENT": os.environ.get("RAILWAY_ENVIRONMENT"),
            "RAILWAY_PROJECT_NAME": os.environ.get("RAILWAY_PROJECT_NAME"),
            "RAILWAY_SERVICE_NAME": os.environ.get("RAILWAY_SERVICE_NAME")
        }
    })

async def ready_check(request):
    """Readiness check endpoint."""
    return web.json_response({
        "status": "ready",
        "message": "Server is ready to accept requests"
    })

async def main():
    """Main server function."""
    # Get port from Railway environment
    port = int(os.environ.get("PORT", "8080"))
    
    logger.info(f"Starting simple health server...")
    logger.info(f"Port: {port}")
    logger.info(f"Railway Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'not_set')}")
    
    # Create app
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/ready", ready_check)
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    logger.info(f"✅ Server started on 0.0.0.0:{port}")
    logger.info("Available endpoints:")
    logger.info("  - GET /ready")
    logger.info("  - GET /health")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await site.stop()
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
