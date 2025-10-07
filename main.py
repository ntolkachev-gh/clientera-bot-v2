#!/usr/bin/env python3
"""
Main entry point for Telegram bot with OpenAI Realtime API.
"""

import asyncio
import sys
import os
import logging
from aiohttp import web

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_immediate_health_server():
    """Start health server immediately, before any imports."""
    try:
        # Only in webhook mode (Railway sets TG_WEBHOOK_URL)
        if not os.environ.get("TG_WEBHOOK_URL"):
            return None, None
            
        port = int(os.environ.get("PORT", "8080"))
        logger.info(f"🚀 MAIN.PY: Starting immediate health server on port {port}")
        
        app = web.Application()
        
        async def health(request):
            return web.json_response({"status": "healthy", "message": "Immediate health server"})
        
        async def ready(request):
            return web.json_response({"status": "ready", "message": "Immediate health server ready"})
        
        app.router.add_get("/health", health)
        app.router.add_get("/ready", ready)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        
        logger.info(f"✅ MAIN.PY: Immediate health server started on port {port}")
        return runner, site
        
    except Exception as e:
        logger.error(f"Failed to start immediate health server: {e}")
        return None, None

async def main():
    """Main entry point with immediate health server."""
    print("🚀 MAIN.PY: Starting new main.py with immediate health server")
    logger.info("🚀 MAIN.PY: Starting new main.py with immediate health server")
    
    health_runner = None
    health_site = None
    
    try:
        # Start health server FIRST, before any heavy imports
        health_runner, health_site = await start_immediate_health_server()
        
        # Give health server time to respond to initial health checks
        await asyncio.sleep(3)
        
        # Stop health server before starting main app (to free the port)
        if health_site:
            await health_site.stop()
            logger.info("Stopped immediate health server")
        if health_runner:
            await health_runner.cleanup()
        
        # Now import and run the main app (which will start its own server)
        from src.app import main as app_main
        await app_main()
        
    except KeyboardInterrupt:
        print("🛑 Application interrupted")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup health server
        if health_site:
            await health_site.stop()
        if health_runner:
            await health_runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Application interrupted")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)