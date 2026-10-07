"""Main entry point for the Universal Media Downloader Bot."""
import asyncio
import os
import signal
import sys
from typing import Optional

from aiogram import Bot, Dispatcher, Router

from bot.config import get_config
from handlers.download import register_download_handler
from handlers.cancel import register_cancel_handler


async def _start_health_server(port: int):
    """Start an aiohttp server exposing GET /health (used by Docker/Render)."""
    from aiohttp import web

    async def health(request: web.Request) -> web.Response:
        return web.json_response({
            "status": "healthy",
            "service": "universal-media-downloader",
            "version": "1.0.0",
        })

    app = web.Application()
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    return runner


def _setup_signal_handlers(stop_event: asyncio.Event) -> None:
    """Ask the main loop to shut down gracefully on SIGINT/SIGTERM."""
    loop = asyncio.get_running_loop()

    def _set_stop() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _set_stop)
        except (NotImplementedError, RuntimeError):
            # Windows / limited platforms
            signal.signal(sig, lambda *a: loop.call_soon_threadsafe(stop_event.set))


async def main():
    """Main application entry point."""
    config = get_config()

    # Check for bot token
    if not config.bot_token:
        print("ERROR: BOT_TOKEN environment variable is not set")
        sys.exit(1)

    from utils.logger import logger
    logger.info("Universal Media Downloader Bot starting...")

    # Ephemeral storage setup (Render /tmp) + cleanup on exit
    from storage.cleanup import TEMP_MANAGER, AUTO_CLEANUP, get_files_in_temp_dir
    TEMP_MANAGER.setup_temp_dirs()

    def _purge_temp_files() -> None:
        for path in get_files_in_temp_dir():
            TEMP_MANAGER.force_delete(path)

    TEMP_MANAGER.add_cleanup_handler(_purge_temp_files)
    AUTO_CLEANUP.register_all()

    # Setup dispatcher & handlers
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    router = Router()
    register_download_handler(router)
    register_cancel_handler(router)
    dp.include_router(router)

    # Health check endpoint (Docker HEALTHCHECK + Render Web Service health check)
    # On Render, PORT is injected — bind to it so Render marks the service healthy.
    # Self-ping in heartbeat keeps the free-tier Web Service from spinning down.
    health_port = int(os.getenv("PORT", os.getenv("HEALTH_PORT", "8082")))
    health_runner = await _start_health_server(health_port)
    logger.info(f"Health check listening on 0.0.0.0:{health_port}/health")

    # Keep-alive heartbeat (prevents Render from sleeping the instance)
    from services.heartbeat import create_heartbeat
    heartbeat = await create_heartbeat(config)

    # Graceful shutdown wiring
    stop_event = asyncio.Event()
    _setup_signal_handlers(stop_event)

    logger.info(
        f"Bot started! Polling as token id: {config.bot_token.split(':')[0]}"
    )
    print("Press Ctrl+C to stop...")

    async def _polling_with_retry(bot: Bot, dp: Dispatcher) -> None:
        """Poll Telegram forever, restarting with backoff after network errors.

        A single transient connection failure must never kill the worker
        (Render would otherwise stay down until the next manual deploy).
        """
        delay = 5
        while not stop_event.is_set():
            try:
                await dp.start_polling(
                    bot, allowed_updates=dp.resolve_used_update_types()
                )
                return  # clean exit from polling
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(f"Polling error, restarting in {delay}s: {exc}")
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=delay)
                    return
                except asyncio.TimeoutError:
                    pass
                delay = min(delay * 2, 60)

    polling_task = asyncio.create_task(_polling_with_retry(bot, dp))
    stop_task = asyncio.create_task(stop_event.wait())

    try:
        await asyncio.wait(
            {polling_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
    finally:
        logger.info("Shutting down...")
        for task in (stop_task, polling_task):
            if not task.done():
                task.cancel()
        await asyncio.gather(polling_task, stop_task, return_exceptions=True)

        await heartbeat.stop()
        await health_runner.cleanup()
        await bot.session.close()

        # Final temp-dir cleanup (atexit handlers)
        AUTO_CLEANUP._cleanup_at_exit()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown requested...")
    finally:
        print("Goodbye!")