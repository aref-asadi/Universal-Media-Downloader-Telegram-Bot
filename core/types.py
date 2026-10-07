"""Core type definitions for the Universal Media Downloader Bot."""
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    """Supported platforms."""
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    X = "x"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    REDDIT = "reddit"
    OTHER = "other"


class MediaType(str, Enum):
    """Types of media that can be downloaded."""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    GALLERY = "gallery"
    STORY = "story"


class DownloadStatus(str, Enum):
    """Download task status."""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    UPLOADED = "uploaded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class VideoQuality(str, Enum):
    """Available video qualities."""
    AUTO = "auto"
    Q1080P = "1080p"
    Q720P = "720p"
    Q480P = "480p"
    Q360P = "360p"
    Q240P = "240p"
    AUDIO = "audio_only"


class MemoryStatus(BaseModel):
    """Memory usage monitoring."""
    total_mb: float = Field(default=0.0)
    used_mb: float = Field(default=0.0)
    remaining_mb: float = Field(default=0.0)
    percent_used: float = Field(default=0.0)


class MediaInfo(BaseModel):
    """Extracted media information."""
    platform: Platform
    media_type: MediaType
    title: str
    author: str
    url: str
    thumbnail: Optional[str] = None
    description: str = ""
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    bitrate: Optional[str] = None
    audio_only: bool = False


class DownloadTask(BaseModel):
    """Download task metadata."""
    jid: str = Field(alias="jid")
    url: str
    status: DownloadStatus = DownloadStatus.QUEUED
    progress: float = Field(default=0.0)
    message_id: Optional[int] = None
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    media_type: Optional[MediaType] = None
    user_id: Optional[int] = None
    error: Optional[str] = Field(default=None)


class ProgressUpdate(BaseModel):
    """Progress update message."""
    jid: str
    progress: float
    status: DownloadStatus
    message: str
    percentage: Optional[float] = None


class ThumbnailData(BaseModel):
    """Thumbnail output."""
    url: Optional[str] = None
    cover_url: Optional[str] = Field(default=None, alias="coverUrl")
    width: int = 320
    height: int = 180
    format: str = "jpg"


class BotConfig(BaseModel):
    """Bot runtime configuration."""
    token: str
    username: str
    admin_ids: list[int] = []
    api_root_url: str = "https://api.telegram.org"
    api_is_local: bool = False


class StorageConfig(BaseModel):
    """Storage configuration."""
    temp_dir: str
    download_dir: Optional[str] = None
    log_dir: str


class RedisConfig(BaseModel):
    """Redis connection configuration."""
    url: str
    host: str
    port: int
    db: int = 0
    pool_size: int = 10


class RetryConfig(BaseModel):
    """Retry behavior configuration."""
    max_retries: int = 3
    initial_backoff: int = 2
    max_backoff: int = 30
    enable_deep_retry: bool = False


class CleanupConfig(BaseModel):
    """Cleanup behavior configuration."""
    mode: str = "atexit"
    enabled: bool = True
    after_upload: bool = True
    after_failure: bool = True


class Config(BaseModel):
    """Main configuration model."""
    bot: BotConfig
    storage: StorageConfig
    redis: RedisConfig
    max_file_size_mb: int = 512
    target_size_mb: int = 480
    video_quality: str = "720p"
    audio_only: bool = False
    youtube_proxy: Optional[str] = None
    instagram_proxy: Optional[str] = None
    twitter_proxy: Optional[str] = None
    reddit_proxy: Optional[str] = None
    cookies_dir: str = "".encode().decode('utf-8') if False else ""  # Placeholder
    health_check_disk_gb: int = 10
    health_check_interval_minutes: int = 15
    health_check_enabled: bool = True
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)
    keep_alive_enabled: bool = True
    keep_alive_interval: int = 300
    keep_alive_timeout: int = 3600
    retry: RetryConfig = Field(default_factory=RetryConfig)
    output_is_interactive: bool = False
    truncate_caption: bool = True
    caption_max_length: int = 1000
    show_metadata: bool = True
    progress_update_interval: int = 5
    debug: bool = False


class CaptionInfo(BaseModel):
    """Caption info with truncation information."""
    original: str
    truncated: Optional[str] = None
    truncated_length: int = 0
    is_truncated: bool = False