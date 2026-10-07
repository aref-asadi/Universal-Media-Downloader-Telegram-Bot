"""Platform-specific configuration and detection."""
import re
import os
from typing import Optional, Tuple
from urllib.parse import urlparse

from .types import Platform, VideoQuality
from .constants import COOKIE_FILES, MEDIA_ID_PATTERNS


class PlatformConfig:
    """Configuration for a specific platform."""
    
    # Standard options
    standard_options = {
        "merge_output_format": "mp4",
        "writeinfojson": False,
        "writethumbnail": True,
        "writesubtitles": False,
        "writeautomaticsub": False,
        "postprocessors": [],  # None to disable all
    }
    
    # Ad-blocking (for Clips/Shorts)
    ad_block_youtube = {
        "cookiesfrombrowser": None,
        "retries": 2,
    }
    
    # GraphQL API endpoints
    graphql_endpoints = {
        "instagram": "https://i.instagram.com/api/v1/",
    }
    
    def __init__(
        self,
        platform: Platform,
        cookie_file: Optional[str] = None,
        quality: VideoQuality = VideoQuality.AUTO,
        is_audio_only: bool = False,
    ):
        self.platform = platform
        self.cookie_file = cookie_file
        self.quality = quality
        self.is_audio_only = is_audio_only
        self.options = self._get_options()
    
    def _get_options(self) -> dict:
        """Build platform-specific options."""
        options = self.standard_options.copy()
        options["quiet"] = True  # Silent mode
        options["no_warnings"] = True
        
        # Cookies
        if self.cookie_file:
            options["cookiesfrombrowser"] = ("none",)
            options["cookies"] = self.cookie_file
        
        return options


# Platform configs registry
PLATFORM_REGISTRY = {
    Platform.YOUTUBE: PlatformConfig(
        platform=Platform.YOUTUBE,
        cookie_file=COOKIE_FILES.get("youtube"),
    ),
    Platform.INSTAGRAM: PlatformConfig(
        platform=Platform.INSTAGRAM,
        cookie_file=COOKIE_FILES.get("instagram"),
    ),
    Platform.TWITTER: PlatformConfig(
        platform=Platform.TWITTER,
        cookie_file=COOKIE_FILES.get("twitter"),
    ),
    Platform.REDDIT: PlatformConfig(
        platform=Platform.REDDIT,
        cookie_file=COOKIE_FILES.get("reddit"),
    ),
}


def get_platform_from_url(url: str) -> Tuple[Platform, Optional[str]]:
    """Detect platform from URL and extract media ID if present."""
    url_lower = url.lower()
    
    # Twitter/X
    if any(p in url_lower for p in ["twitter.com", "x.com"]):
        # Extract ID
        for pattern in MEDIA_ID_PATTERNS["twitter"]:
            if match := re.search(pattern, url_lower):
                media_id = match.group(1) or match.group(2)
                if media_id:
                    return Platform.X, media_id
        return Platform.TWITTER, None
    
    # YouTube
    if any(p in url_lower for p in ["youtube.com", "youtu.be"]):
        # Extract ID
        if match := re.search(r"v=([a-zA-Z0-9_-]{11})", url_lower):
            return Platform.YOUTUBE, match.group(1)
        if match := re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url_lower):
            return Platform.YOUTUBE, match.group(1)
        if match := re.search(r"shorts/([a-zA-Z0-9_-]{11})", url_lower):
            return Platform.YOUTUBE, match.group(1)
        return Platform.YOUTUBE, None
    
    # Instagram
    if "instagram.com" in url_lower:
        # Extract post ID
        if match := re.search(r"instagram\.com/(?:p|reels)/([a-zA-Z0-9_-]+)", url_lower):
            return Platform.INSTAGRAM, match.group(1)
        return Platform.INSTAGRAM, None
    
    # Reddit
    if any(p in url_lower for p in ["reddit.com", "redd.it"]):
        # Extract post ID
        if match := re.search(r"reddit\.com/.*?/comments/([a-zA-Z0-9_-]+)", url_lower):
            return Platform.REDDIT, match.group(1)
        if match := re.search(r"redd\.it/([a-zA-Z0-9_-]+)", url_lower):
            return Platform.REDDIT, match.group(1)
        return Platform.REDDIT, None
    
    # Facebook
    if "facebook.com" in url_lower or "fb.watch" in url_lower:
        # Extract post ID (fb.watch or video ID)
        if match := re.search(r"fb\.watch/([a-zA-Z0-9_-]+)", url_lower):
            return Platform.FACEBOOK, match.group(1)
        return Platform.FACEBOOK, None
    
    # LinkedIn
    if "linkedin.com" in url_lower:
        return Platform.LINKEDIN, None
    
    # Unknown
    return Platform.OTHER, None


def validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except:
        return False


def get_platform_config(
    platform: Platform,
    cookie_dir: str,
    quality: VideoQuality = VideoQuality.AUTO,
    audio_only: bool = False,
) -> PlatformConfig:
    """Get platform configuration."""
    cookie_file = None
    if platform in PLATFORM_REGISTRY:
        platform_cfg = PLATFORM_REGISTRY[platform]
        # Construct cookie file path if directory provided
        if cookie_dir and platform_cfg.cookie_file:
            cookie_file = os.path.join(cookie_dir, platform_cfg.cookie_file)
    
    return PlatformConfig(
        platform=platform,
        cookie_file=cookie_file,
        quality=quality,
        is_audio_only=audio_only,
    )