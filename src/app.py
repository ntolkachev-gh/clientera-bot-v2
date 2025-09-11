#!/usr/bin/env python3
"""
Main application entry point for Telegram bot with OpenAI Realtime API.
"""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from .config.env import get_settings
from .integrations.cache import cleanup_cache
from .integrations.yclients_adapter import get_yclients_adapter
from .realtime.client import cleanup_realtime_client, get_realtime_client
from .realtime.connection_pool import cleanup_connection_pool, get_connection_pool
from .telegram.handlers import get_handlers_router
from .utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


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
            return web.json_response({
                "status": "healthy",
                "bot_info": {
                    "id": self.bot.id,
                    "username": (await self.bot.get_me()).username
                }
            })
        
        app.router.add_get("/health", health_check)
        
        # Setup application
        setup_application(app, self.dp, bot=self.bot)
        
        logger.info("Web application created")
        return app
    
    async def start_webhook_server(self) -> None:
        """Start webhook server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(
            self.runner,
            host="0.0.0.0",
            port=settings.TG_WEBHOOK_PORT
        )
        
        await self.site.start()
        logger.info(f"Webhook server started on port {settings.TG_WEBHOOK_PORT}")
    
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
                    from .utils.throttler import get_message_throttler, get_rate_limiter
                    throttler = get_message_throttler()
                    rate_limiter = get_rate_limiter()
                    
                    throttler.cleanup_old_entries()
                    rate_limiter.cleanup_old_entries()
                    
                    # Clean up finished streams and perform health check
                    if self.connection_pool:
                        await self.connection_pool.health_check()
                        
                        # Log pool stats periodically
                        stats = self.connection_pool.get_pool_stats()
                        logger.info(f"📊 Pool stats: {stats['total_active_users']} active users, "
                                  f"{stats['healthy_connections']}/{stats['pool_size']} healthy connections")
                    
                    logger.debug("Background cleanup completed")
                    
                except Exception as e:
                    logger.error(f"Error in background cleanup: {e}")
                
                # Run cleanup every 5 minutes
                await asyncio.sleep(300)
        
        asyncio.create_task(cleanup_task())
        logger.info("Background cleanup task started")
    
    async def startup(self) -> None:
        """Application startup."""
        logger.info("Starting Telegram bot application...")
        logger.info(f"Configuration: {settings.mask_sensitive_data()}")
        
        # Create bot and dispatcher
        self.bot = await self.create_bot()
        self.dp = await self.create_dispatcher()
        
        # Initialize Realtime client
        await self.initialize_realtime_client()
        
        # Start background tasks
        await self.cleanup_background_tasks()
        
        # Set up webhook or polling based on configuration
        if settings.TG_WEBHOOK_URL:
            # Production: webhook mode
            await self.setup_webhook()
            self.app = await self.create_web_app()
            await self.start_webhook_server()
            
            logger.info("🚀 Bot started in webhook mode")
            logger.info(f"📡 Webhook URL: {settings.TG_WEBHOOK_URL}{settings.TG_WEBHOOK_PATH}")
            logger.info(f"🌐 Server listening on port {settings.TG_WEBHOOK_PORT}")
        
        else:
            # Development: polling mode
            logger.info("🚀 Bot started in polling mode")
            logger.info("📡 Using long polling for development")
            
            # Start polling
            await self.dp.start_polling(
                self.bot,
                skip_updates=True,
                allowed_updates=["message", "callback_query"]
            )
    
    async def shutdown(self) -> None:
        """Application shutdown."""
        logger.info("Shutting down Telegram bot application...")
        
        # Stop webhook server
        await self.stop_webhook_server()
        
        # Close bot session
        if self.bot:
            await self.bot.session.close()
        
        # Cleanup connection pool
        await cleanup_connection_pool()
        
        # Cleanup single client if it exists
        await cleanup_realtime_client()
        
        # Cleanup cache
        cleanup_cache()
        
        logger.info("👋 Application shutdown completed")


# Global app instance
app_instance: TelegramBotApp = None


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


async def main():
    """Main application entry point."""
    try:
        setup_signal_handlers()
        
        if settings.TG_WEBHOOK_URL:
            await run_webhook_mode()
        else:
            await run_polling_mode()
    
    except KeyboardInterrupt:
        logger.info("🛑 Application interrupted by user")
    
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Application interrupted")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)
