"""Bot configuration manager."""
import os
from typing import Optional
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.constants import RENDER_ENV_KEY, RENDER_REDIS_URL_KEY


@lru_cache(maxsize=1)
def load_config() -> "BotSettings":
    """Load configuration from environment variables / .env file.

    load_dotenv() never overrides variables that are already set in the
    environment, so Render/Docker env vars take precedence over .env.
    """
    load_dotenv()
    return BotSettings()


class BotSettings(BaseSettings):
    """Bot runtime settings."""
    
    RENDER_ENV_KEY: str = RENDER_ENV_KEY
    RENDER_REDIS_URL_KEY: str = RENDER_REDIS_URL_KEY
    
    bot_token: str = Field(min_length=1)
    bot_username: str = Field(default="")
    admin_ids: str = Field(default="")
    
    telegram_api_root_url: str = Field(default="https://api.telegram.org")
    telegram_api_is_local: bool = Field(default=False)
    telegram_api_token: str = Field(default="")
    telegram_api_port: int = Field(default=8081)
    
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: str = Field(default="")
    redis_pool_size: int = Field(default=5)
    
    max_file_size_mb: int = Field(default=512)
    target_size_mb: int = Field(default=480)
    video_quality: str = Field(default="720p")
    audio_only: bool = Field(default=False)
    
    youtube_proxy: str = Field(default="")
    instagram_proxy: str = Field(default="")
    twitter_proxy: str = Field(default="")
    reddit_proxy: str = Field(default="")
    
    cookies_dir: str = Field(default="~/.yt-dlp/cookies")
    temp_dir: str = Field(default="/tmp/ubd")
    download_dir: Optional[str] = Field(default=None)
    log_dir: str = Field(default="/tmp/ubd/logs")
    
    health_check_disk_gb: int = Field(default=10)
    health_check_interval_minutes: int = Field(default=15)
    health_check_enabled: bool = Field(default=True)
    
    auto_cleanup_mode: str = Field(default="atexit")
    auto_cleanup_enabled: bool = Field(default=True)
    cleanup_after_upload: bool = Field(default=True)
    cleanup_after_failure: bool = Field(default=True)
    
    keep_alive_enabled: bool = Field(default=True)
    keep_alive_interval: int = Field(default=300)
    keep_alive_timeout: int = Field(default=3600)
    
    max_retries: int = Field(default=3)
    initial_backoff: int = Field(default=2)
    max_backoff: int = Field(default=30)
    
    output_is_interactive: bool = Field(default=False)
    truncate_caption: bool = Field(default=True)
    caption_max_length: int = Field(default=1000)
    show_metadata: bool = Field(default=True)
    
    progress_update_interval: int = Field(default=5)
    progress_format: str = Field(default="short")
    
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    monitor_memory: bool = Field(default=False)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    @field_validator("debug", "telegram_api_is_local", "audio_only",
                     "auto_cleanup_enabled", "cleanup_after_upload",
                     "cleanup_after_failure", "keep_alive_enabled",
                     "health_check_enabled", "output_is_interactive",
                     "truncate_caption", "monitor_memory", mode="before")
    @classmethod
    def _coerce_bool(cls, v):
        """Tolerate non-boolean env vars (e.g. a system-wide DEBUG=WARN)."""
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return v

    @property
    def admin_id_list(self) -> list[int]:
        if not self.admin_ids:
            return []
        try:
            return [int(aid.strip()) for aid in self.admin_ids.split(",") if aid.strip()]
        except ValueError:
            return []
    
    @property
    def pool_size(self) -> int:
        if "RENDER" in os.environ or "render" in os.environ.lower():
            return min(self.redis_pool_size, 2)
        return max(self.redis_pool_size, 10)
    
    @property
    def redis_kwargs(self) -> dict:
        kwargs = {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "decode_responses": True,
        }
        if self.redis_password:
            kwargs["password"] = self.redis_password
        return kwargs


config = load_config()


def get_config() -> BotSettings:
    """Get the global configuration instance."""
    return config


def reload_config() -> BotSettings:
    """Force reload of configuration."""
    global config
    config = load_config()
    return config