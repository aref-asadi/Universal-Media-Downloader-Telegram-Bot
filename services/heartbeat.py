"""Heartbeat service to prevent Render sleep."""
import asyncio
import os
from typing import Optional

import redis.asyncio as redis

from utils.logger import logger


class Heartbeat:
    """Keep-alive service to prevent Render from sleeping the container.

    On Render's free Web Service tier the instance spins down after ~15 min
    of no inbound HTTP traffic. We beat that by self-pinging our own /health
    endpoint every KEEP_ALIVE_INTERVAL seconds using Render's injected
    RENDER_EXTERNAL_URL. We also write a Redis heartbeat key so external
    monitors can verify the bot is alive.
    """

    def __init__(self, config):
        self.config = config
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._redis_url = self._get_redis_url()

    def _get_redis_url(self) -> str:
        """Get Redis URL from config or environment."""
        if "RENDER_REDIS_URL" in os.environ:
            return os.environ["RENDER_REDIS_URL"]
        if "REDIS_URL" in os.environ:
            return os.environ["REDIS_URL"]
        return f"redis://{self.config.redis_host}:{self.config.redis_port}"

    def _get_self_ping_url(self) -> Optional[str]:
        """Build the URL to self-ping.

        Render injects RENDER_EXTERNAL_URL for Web Services, e.g.
        https://universal-media-downloader.onrender.com
        """
        base = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
        if base:
            return f"{base}/health"
        # Local dev: use the configured health port
        port = os.getenv("PORT", os.getenv("HEALTH_PORT", "8082"))
        return f"http://localhost:{port}/health"

    async def start(self):
        """Start heartbeat."""
        if not self.config.keep_alive_enabled:
            logger.info("Heartbeat disabled in config")
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Heartbeat service started")

    async def stop(self):
        """Stop heartbeat."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat service stopped")

    async def _ping_redis(self) -> None:
        """Write a heartbeat key to Redis so external monitors can check it."""
        try:
            r = redis.from_url(self._redis_url, decode_responses=True)
            await r.ping()
            await r.setex(
                "ubd:heartbeat",
                self.config.keep_alive_timeout,
                str(os.getpid()),
            )
            await r.aclose()
        except Exception as e:
            logger.debug(f"Redis heartbeat failed: {e}")

    async def _ping_self(self) -> None:
        """HTTP GET our own /health to prevent Render free-tier spin-down."""
        url = self._get_self_ping_url()
        if not url:
            return
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    logger.debug(f"Self-ping {url} -> {resp.status}")
        except Exception as e:
            logger.debug(f"Self-ping failed: {e}")

    async def _run(self):
        """Run heartbeat loop."""
        while self._running:
            await self._ping_redis()
            await self._ping_self()
            await asyncio.sleep(self.config.keep_alive_interval)


async def create_heartbeat(config) -> Heartbeat:
    """Factory function to create heartbeat."""
    hb = Heartbeat(config)
    await hb.start()
    return hb
