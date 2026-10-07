"""Heartbeat service to prevent Render sleep."""
import asyncio
import os
import logging
from typing import Optional

import redis.asyncio as redis

from utils.logger import logger


class Heartbeat:
    """Keep-alive service to prevent Render from sleeping the container."""
    
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
    
    async def start(self):
        """Start heartbeat."""
        if not self.config.keep_alive_enabled:
            logger.info("Heartbeat disabled in config")
            return
        
        if "RENDER" not in os.environ and "render" not in os.environ.get("RENDER", "").lower():
            logger.info("Not running on Render, heartbeat optional")
            # Still start it for local dev
        
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
    
    async def _run(self):
        """Run heartbeat loop."""
        while self._running:
            try:
                # Create connection
                r = redis.from_url(self._redis_url, decode_responses=True)
                await r.ping()
                
                # Set heartbeat key with TTL
                await r.setex(
                    "ubd:heartbeat",
                    self.config.keep_alive_timeout,
                    str(os.getpid())
                )
                
                await r.aclose()
                
                logger.debug("Heartbeat ping sent")
            except Exception as e:
                logger.debug(f"Heartbeat ping failed: {e}")
            
            await asyncio.sleep(self.config.keep_alive_interval)


async def create_heartbeat(config) -> Heartbeat:
    """Factory function to create heartbeat."""
    hb = Heartbeat(config)
    await hb.start()
    return hb