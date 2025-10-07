#!/usr/bin/env python3
"""
Main application entry point for Telegram bot with OpenAI Realtime API.
"""

import asyncio
import fcntl
import os
import signal
import sys
from contextlib import asynccontextmanager
from typing import Dict, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

try:
    # Попытка относительного импорта (когда запускается как модуль)
    from .config.env import get_settings
    from .integrations.cache import cleanup_cache
    from .integrations.yclients_adapter import get_yclients_adapter
    from .realtime.client import cleanup_realtime_client, get_realtime_client
    from .realtime.connection_pool import cleanup_connection_pool, get_connection_pool
    from .telegram.handlers import get_handlers_router
    from .utils.logger import get_logger
except ImportError:
    # Абсолютный импорт (когда запускается напрямую)
    from src.config.env import get_settings
    from src.integrations.cache import cleanup_cache
    from src.integrations.yclients_adapter import get_yclients_adapter
    from src.realtime.client import cleanup_realtime_client, get_realtime_client
    from src.realtime.connection_pool import cleanup_connection_pool, get_connection_pool
    from src.telegram.handlers import get_handlers_router
    from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# User inactivity timeout (1 hour)
INACTIVITY_TIMEOUT = 3600


class TelegramBotApp:
    """Main Telegram bot application."""
    
    def __init__(self):
        self.bot: Bot = None
        self.dp: Dispatcher = None
        self.app: web.Application = None
        self.runner: web.AppRunner = None
        self.site: web.TCPSite = None
        self.realtime_client = None
        self.connection_pool = None
        self.user_inactivity_timers: Dict[int, asyncio.Task] = {}
        self._process_lock_fd = None
    
    def acquire_process_lock(self) -> None:
        """Acquire process lock to prevent multiple instances."""
        lock_file = "/tmp/dental_bot.lock"
        try:
            self._process_lock_fd = open(lock_file, 'w')
            fcntl.lockf(self._process_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._process_lock_fd.write(str(os.getpid()))
            self._process_lock_fd.flush()
            logger.info("Process lock acquired successfully")
        except IOError:
            logger.error("Another instance is already running!")
            logger.error("Check processes: ps aux | grep dental_bot")
            sys.exit(1)
    
    def release_process_lock(self) -> None:
        """Release process lock."""
        if self._process_lock_fd:
            try:
                self._process_lock_fd.close()
                os.unlink("/tmp/dental_bot.lock")
                logger.info("Process lock released")
            except Exception as e:
                logger.warning(f"Failed to release process lock: {e}")
    
    async def reset_user_inactivity_timer(self, user_id: int) -> None:
        """Reset inactivity timer for user."""
        # Cancel existing timer
        if user_id in self.user_inactivity_timers:
            self.user_inactivity_timers[user_id].cancel()
        
        # Create new timer
        async def timeout_handler():
            try:
                await asyncio.sleep(INACTIVITY_TIMEOUT)
                logger.info(f"User {user_id} inactivity timeout reached")
                
                # Cancel active streams for this user
                if self.connection_pool:
                    try:
                        await self.connection_pool.cancel_user_streams(user_id)
                        logger.info(f"Cancelled streams for inactive user {user_id}")
                    except Exception as e:
                        logger.error(f"Error cancelling streams for user {user_id}: {e}")
                
                # Remove timer
                if user_id in self.user_inactivity_timers:
                    del self.user_inactivity_timers[user_id]
                    
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in inactivity timeout handler: {e}")
        
        # Start new timer
        self.user_inactivity_timers[user_id] = asyncio.create_task(timeout_handler())
        logger.debug(f"🔄 Inactivity timer reset for user {user_id}")
    
    async def cancel_user_inactivity_timer(self, user_id: int) -> None:
        """Cancel inactivity timer for user."""
        if user_id in self.user_inactivity_timers:
            self.user_inactivity_timers[user_id].cancel()
            del self.user_inactivity_timers[user_id]
            logger.debug(f"Inactivity timer cancelled for user {user_id}")
        
    async def create_bot(self) -> Bot:
        """Create and configure bot instance."""
        bot = Bot(
            token=settings.TG_BOT_TOKEN,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
                link_preview_is_disabled=True
            )
        )
        
        logger.info("Bot instance created")
        return bot
    
    async def create_dispatcher(self) -> Dispatcher:
        """Create and configure dispatcher."""
        dp = Dispatcher()
        
        # Include handlers router
        dp.include_router(get_handlers_router())
        
        logger.info("Dispatcher configured with handlers")
        return dp
    
    async def setup_webhook(self) -> None:
        """Set up webhook for production."""
        if not settings.TG_WEBHOOK_URL:
            logger.warning("TG_WEBHOOK_URL not set, skipping webhook setup")
            return
        
        webhook_url = f"{settings.TG_WEBHOOK_URL}{settings.TG_WEBHOOK_PATH}"
        
        try:
            await self.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            logger.info(f"Webhook set to: {webhook_url}")
        
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            raise
    
    async def create_web_app(self) -> web.Application:
        """Create aiohttp web application for webhook."""
        app = web.Application()
        
        # Webhook handler
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=self.dp,
            bot=self.bot,
        )
        webhook_requests_handler.register(app, path=settings.TG_WEBHOOK_PATH)
        
        # Health check endpoint
        async def health_check(request):
            try:
                # Basic health check - just return that the service is running
                health_data = {
                    "status": "healthy",
                    "service": "telegram-bot",
                    "timestamp": asyncio.get_event_loop().time()
                }
                
                # Try to get bot info if bot is available, but don't fail if it's not
                if self.bot:
                    try:
                        bot_me = await self.bot.get_me()
                        health_data["bot_info"] = {
                            "id": self.bot.id,
                            "username": bot_me.username,
                            "first_name": bot_me.first_name
                        }
                    except Exception as e:
                        # Log the error but don't fail the health check
                        logger.warning(f"Could not get bot info for health check: {e}")
                        health_data["bot_info"] = {"status": "unavailable", "error": str(e)}
                
                return web.json_response(health_data)
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return web.json_response({
                    "status": "unhealthy",
                    "error": str(e)
                }, status=503)
        
        app.router.add_get("/health", health_check)
        
        # Add a simple readiness check that doesn't depend on bot initialization
        async def readiness_check(request):
            return web.json_response({
                "status": "ready",
                "service": "telegram-bot",
                "message": "Service is fully initialized and ready to accept requests"
            })
        
        app.router.add_get("/ready", readiness_check)
        
        # Setup application
        setup_application(app, self.dp, bot=self.bot)
        
        logger.info("Web application created")
        return app
    
    async def start_webhook_server(self) -> None:
        """Start webhook server."""
        webhook_port = settings.get_webhook_port()
        logger.info(f"Starting webhook server on 0.0.0.0:{webhook_port}")
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(
            self.runner,
            host="0.0.0.0",
            port=webhook_port
        )
        
        await self.site.start()
        logger.info(f"✅ Webhook server started successfully on port {webhook_port}")
        logger.info(f"Health endpoints available at:")
        logger.info(f"  - /ready (simple readiness check)")
        logger.info(f"  - /health (detailed health check)")
    
    async def stop_webhook_server(self) -> None:
        """Stop webhook server."""
        if self.site:
            await self.site.stop()
            logger.info("Webhook server stopped")
        
        if self.runner:
            await self.runner.cleanup()
    
    async def initialize_realtime_client(self) -> None:
        """Initialize OpenAI Realtime connection pool."""
        try:
            yclients_adapter = get_yclients_adapter()
            
            # Initialize connection pool instead of single client
            self.connection_pool = await get_connection_pool(
                yclients_adapter=yclients_adapter,
                pool_size=settings.WS_POOL_SIZE
            )
            logger.info(f"Connection pool initialized with {settings.WS_POOL_SIZE} connections")
            
            # Keep single client for backwards compatibility if needed
            # self.realtime_client = await get_realtime_client(yclients_adapter)
        
        except Exception as e:
            logger.error(f"Failed to initialize Realtime connection pool: {e}")
            raise
    
    async def cleanup_background_tasks(self) -> None:
        """Start background cleanup tasks."""
        async def cleanup_task():
            while True:
                try:
                    # Clean up throttler entries
                    try:
                        from .utils.throttler import get_message_throttler, get_rate_limiter
                    except ImportError:
                        from src.utils.throttler import get_message_throttler, get_rate_limiter
                    throttler = get_message_throttler()
                    rate_limiter = get_rate_limiter()
                    
                    throttler.cleanup_old_entries()
                    rate_limiter.cleanup_old_entries()
                    
                    # Clean up finished streams and perform health check
                    if self.connection_pool:
                        await self.connection_pool.health_check()
                        
                        # Log pool stats periodically
                        stats = self.connection_pool.get_pool_stats()
                        logger.info(f"Pool stats: {stats['total_active_users']} active users, "
                                  f"{stats['healthy_connections']}/{stats['pool_size']} healthy connections")
                    
                    logger.debug("Background cleanup completed")
                    
                except Exception as e:
                    logger.error(f"Error in background cleanup: {e}")
                
                # Run cleanup every 5 minutes
                await asyncio.sleep(300)
        
        asyncio.create_task(cleanup_task())
        logger.info("Background cleanup task started")
    
    async def start_early_health_server(self) -> None:
        """Start a simple health server early in the startup process."""
        if not settings.TG_WEBHOOK_URL:
            return  # Only needed in webhook mode
            
        from aiohttp import web
        
        # Create minimal app with just health endpoints
        early_app = web.Application()
        
        async def early_ready_check(request):
            return web.json_response({
                "status": "starting",
                "service": "telegram-bot",
                "message": "Service is starting up"
            })
        
        async def early_health_check(request):
            return web.json_response({
                "status": "initializing",
                "service": "telegram-bot",
                "message": "Service is initializing"
            })
        
        early_app.router.add_get("/ready", early_ready_check)
        early_app.router.add_get("/health", early_health_check)
        
        # Start early server
        self.early_runner = web.AppRunner(early_app)
        await self.early_runner.setup()
        
        webhook_port = settings.get_webhook_port()
        self.early_site = web.TCPSite(
            self.early_runner,
            host="0.0.0.0",
            port=webhook_port
        )
        
        await self.early_site.start()
        logger.info(f"🚀 Early health server started on port {webhook_port} (Railway PORT: {os.environ.get('PORT', 'not_set')})")

    async def stop_early_health_server(self) -> None:
        """Stop early health server."""
        if hasattr(self, 'early_site') and self.early_site:
            await self.early_site.stop()
            logger.info("Early health server stopped")
        
        if hasattr(self, 'early_runner') and self.early_runner:
            await self.early_runner.cleanup()

    async def startup(self) -> None:
        """Application startup."""
        try:
            # Acquire process lock first
            self.acquire_process_lock()
            
            logger.info("TBA_STU: Starting Telegram bot application...")
            logger.info(f"TBA_STU: Configuration: {settings.mask_sensitive_data()}")
            
            # Log environment diagnostics
            webhook_port = settings.get_webhook_port()
            logger.info(f"TBA_STU: Environment diagnostics:")
            logger.info(f"  - Railway PORT: {os.environ.get('PORT', 'not_set')}")
            logger.info(f"  - TG_WEBHOOK_PORT: {settings.TG_WEBHOOK_PORT}")
            logger.info(f"  - Effective port: {webhook_port}")
            logger.info(f"  - TG_WEBHOOK_URL: {settings.TG_WEBHOOK_URL}")
            
            # Skip early health server - standalone server is already running
            logger.info("TBA_STU: Standalone health server already running, skipping early server...")
            
            # Create bot and dispatcher
            logger.info("TBA_STU: Creating bot instance...")
            self.bot = await self.create_bot()
            logger.info("TBA_STU: Creating dispatcher...")
            self.dp = await self.create_dispatcher()
            
            # Initialize Realtime client
            logger.info("TBA_STU: Initializing Realtime client...")
            await self.initialize_realtime_client()
            
            # Start background tasks
            logger.info("TBA_STU: Starting background tasks...")
            await self.cleanup_background_tasks()
            
        except Exception as e:
            logger.error(f"TBA_STU: Failed during startup initialization: {e}")
            # Make sure early health server is stopped on error
            await self.stop_early_health_server()
            raise
        
        # Set up webhook or polling based on configuration
        try:
            if settings.TG_WEBHOOK_URL:
                # Production: webhook mode
                logger.info("TBA_STU: Setting up webhook mode...")
                
                # Note: Standalone health server will be replaced by main server
                # No need to stop it explicitly - it will be replaced on the same port
                
                # Create main web app (this starts the full health endpoint)
                logger.info("TBA_STU: Creating main web application...")
                self.app = await self.create_web_app()
                
                logger.info("TBA_STU: Starting main webhook server...")
                await self.start_webhook_server()
                
                # Then set up webhook (this requires the server to be running)
                logger.info("TBA_STU: Setting up Telegram webhook...")
                await self.setup_webhook()
                
                webhook_port = settings.get_webhook_port()
                logger.info("TBA_STU: ✅ Bot started in webhook mode")
                logger.info(f"TBA_STU: Webhook URL =  {settings.TG_WEBHOOK_URL}{settings.TG_WEBHOOK_PATH}")
                logger.info(f"TBA_STU: Server listening on port {webhook_port}")
            
            else:
                # Development: polling mode
                logger.info("TBA_STU: Bot started in polling mode")
                logger.info("TBA_STU: Using long polling for development")
                
                # Start polling
                await self.dp.start_polling(
                    self.bot,
                    skip_updates=True,
                    allowed_updates=["message", "callback_query"]
                )
                
        except Exception as e:
            logger.error(f"TBA_STU: Failed during webhook/polling setup: {e}")
            # Make sure servers are stopped on error
            await self.stop_webhook_server()
            await self.stop_early_health_server()
            raise
    
    async def shutdown(self) -> None:
        """Application shutdown."""
        logger.info("TBA_SHD: Shutting down Telegram bot application...")
        
        # Cancel all inactivity timers
        for user_id in list(self.user_inactivity_timers.keys()):
            await self.cancel_user_inactivity_timer(user_id)
        logger.info("TBA_SHD: All inactivity timers cancelled")
        
        # Stop webhook server
        await self.stop_webhook_server()
        
        # Stop early health server if still running
        await self.stop_early_health_server()
        
        # Close bot session
        if self.bot:
            await self.bot.session.close()
        
        # Cleanup connection pool
        await cleanup_connection_pool()
        
        # Cleanup single client if it exists
        await cleanup_realtime_client()
        
        # Cleanup cache
        await cleanup_cache()
        
        # Release process lock
        self.release_process_lock()
        
        logger.info("TBA_SHD: Application shutdown completed")


# Global app instance
app_instance: TelegramBotApp = None


def get_app_instance() -> Optional[TelegramBotApp]:
    """Get global app instance."""
    return app_instance


async def reset_user_inactivity_timer_global(user_id: int) -> None:
    """Global function to reset user inactivity timer."""
    if app_instance:
        await app_instance.reset_user_inactivity_timer(user_id)


@asynccontextmanager
async def lifespan_context():
    """Application lifespan context manager."""
    global app_instance
    
    app_instance = TelegramBotApp()
    
    try:
        await app_instance.startup()
        yield app_instance
    
    finally:
        await app_instance.shutdown()


async def run_webhook_mode():
    """Run bot in webhook mode."""
    async with lifespan_context() as app:
        # Health server is handled in main.py
        # Keep the application running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Webhook mode cancelled")


async def run_polling_mode():
    """Run bot in polling mode."""
    async with lifespan_context() as app:
        # Polling is handled in startup()
        pass


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        
        # Cancel all running tasks
        for task in asyncio.all_tasks():
            if not task.done():
                task.cancel()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def start_standalone_health_server():
    """Start standalone health server that runs independently."""
    if not settings.TG_WEBHOOK_URL:
        return None, None  # Only needed in webhook mode
        
    from aiohttp import web
    
    # Create minimal app with just health endpoints
    health_app = web.Application()
    
    async def standalone_ready_check(request):
        return web.json_response({
            "status": "ready",
            "service": "telegram-bot",
            "message": "Standalone health server running",
            "main_app_status": "initializing"
        })
    
    async def standalone_health_check(request):
        return web.json_response({
            "status": "healthy",
            "service": "telegram-bot", 
            "message": "Standalone health server healthy",
            "main_app_status": "initializing"
        })
    
    health_app.router.add_get("/ready", standalone_ready_check)
    health_app.router.add_get("/health", standalone_health_check)
    
    # Start standalone server
    webhook_port = settings.get_webhook_port()
    runner = web.AppRunner(health_app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", webhook_port)
    await site.start()
    
    logger.info(f"🚀 Standalone health server started on port {webhook_port}")
    return runner, site

async def stop_standalone_health_server(runner, site):
    """Stop standalone health server."""
    if site:
        await site.stop()
        logger.info("Standalone health server stopped")
    if runner:
        await runner.cleanup()

async def main():
    """Main application entry point."""
    standalone_runner = None
    standalone_site = None
    
    try:
        setup_signal_handlers()
        
        # Health server is handled in main.py, no need for standalone server here
        if settings.TG_WEBHOOK_URL:
            await run_webhook_mode()
        else:
            await run_polling_mode()
    
    except KeyboardInterrupt:
        logger.info("🛑 Application interrupted by user")
    
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)
    
    finally:
        # Always cleanup standalone health server
        if standalone_runner or standalone_site:
            await stop_standalone_health_server(standalone_runner, standalone_site)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Application interrupted")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)
