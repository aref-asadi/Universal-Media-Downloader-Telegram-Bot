"""ARQ task worker for background downloads."""
import os
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime

import redis.asyncio as redis
from arq import create_pool, Worker
from arq.connections import RedisSettings as ARQRedisSettings

from core.types import DownloadStatus, MediaType
from core.errors import normalize_error
from utils.logger import logger


class DownloadWorker:
    """Background worker for handling downloads."""
    
    def __init__(self, config, bot=None):
        self.config = config
        self.bot = bot
        self.redis_pool: Optional[redis.ConnectionPool] = None
        self._running = False
    
    async def start(self):
        """Start the worker."""
        self._running = True
        self.redis_pool = redis.from_url(
            f"redis://{self.config.redis_host}:{self.config.redis_port}/{self.config.redis_db}",
            decode_responses=True,
        )
        await self.redis_pool.ping()
        logger.info("Download worker started")
    
    async def stop(self):
        """Stop the worker."""
        self._running = False
        if self.redis_pool:
            await self.redis_pool.aclose()
        logger.info("Download worker stopped")
    
    async def enqueue_download(self, job_data: Dict[str, Any]) -> str:
        """Enqueue a download job."""
        import uuid
        job_id = str(uuid.uuid4())
        job_data["jid"] = job_id
        job_data["status"] = DownloadStatus.QUEUED.value
        job_data["created_at"] = datetime.utcnow().isoformat()
        
        # Store job in Redis
        await self.redis_pool.hset(f"job:{job_id}", mapping=job_data)
        
        # Add to queue
        await self.redis_pool.lpush("download_queue", job_id)
        
        logger.info(f"Enqueued download job: {job_id}")
        return job_id
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        job = await self.redis_pool.hgetall(f"job:{job_id}")
        if not job:
            return {"status": "not_found"}
        return job
    
    async def process_job(self, job_id: str):
        """Process a download job (placeholder for actual processing)."""
        job = await self.redis_pool.hgetall(f"job:{job_id}")
        if not job:
            return
        
        await self.redis_pool.hset(f"job:{job_id}", "status", DownloadStatus.DOWNLOADING.value)
        
        try:
            # This would actually call the extractor/download logic
            # For now, just simulate completion
            await asyncio.sleep(2)
            
            await self.redis_pool.hset(f"job:{job_id}", mapping={
                "status": DownloadStatus.COMPLETED.value,
                "completed_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            await self.redis_pool.hset(f"job:{job_id}", mapping={
                "status": DownloadStatus.FAILED.value,
                "error": str(e),
            })
            logger.error(f"Job {job_id} failed: {normalize_error(e)}")


# Job functions for ARQ
async def download_media_job(ctx: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
    """ARQ job function for downloading media."""
    job_id = job_data.get("jid")
    url = job_data.get("url")
    chat_id = job_data.get("chat_id")
    
    try:
        # Import locally to avoid circular imports
        from services.extractor import create_extractor
        from services.ffmpeg import ffmpeg_processor
        from bot.config import get_config
        
        config = get_config()
        extractor = create_extractor(config)
        
        # Update progress
        await ctx["redis"].hset(f"job:{job_id}", "progress", 10)
        
        # Download
        temp_dir = f"/tmp/ubd/{job_id}"
        os.makedirs(temp_dir, exist_ok=True)
        
        await ctx["redis"].hset(f"job:{job_id}", "progress", 30)
        
        file_path = await extractor.download_media(url, temp_dir)
        
        await ctx["redis"].hset(f"job:{job_id}", "progress", 60)
        
        # Extract thumbnail
        thumb_path = os.path.join(temp_dir, "thumb.jpg")
        if os.path.exists(file_path):
            try:
                await ffmpeg_processor.extract_thumbnail(file_path, thumb_path)
            except:
                thumb_path = None
        
        await ctx["redis"].hset(f"job:{job_id}", "progress", 80)
        
        # Upload (would need bot instance)
        # result = await uploader.upload_video(chat_id, file_path, thumb_path=thumb_path)
        
        return {"status": "completed", "file": file_path, "thumb": thumb_path}
    
    except Exception as e:
        logger.error(f"Download job failed: {normalize_error(e)}")
        return {"status": "failed", "error": str(e)}


async def startup(ctx):
    """Worker startup."""
    logger.info("ARQ worker starting")


async def shutdown(ctx):
    """Worker shutdown."""
    logger.info("ARQ worker shutting down")


class WorkerSettings:
    """ARQ Worker settings."""
    functions = [download_media_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = ARQRedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    max_jobs = 1
    job_timeout = 600
    keep_result = 3600


# For local testing
async def run_worker():
    """Run ARQ worker standalone."""
    import arq
    worker = arq.worker.Worker(WorkerSettings())
    await worker.start()


if __name__ == "__main__":
    asyncio.run(run_worker())