"""Constants for the Universal Media Downloader Bot."""
from urllib.parse import urlparse


# ==================== Security ====================
# 512 MB for Render deployment
MAX_REQUEST_SIZE_MB = 512
DEFAULT_TARGET_SIZE_MB = 480

# Telegram API
MAX_CAPTION_LENGTH = 4096
TRUNCATE_LIMIT = 1000

# Timeouts
REQUEST_TIMEOUT = 300
DOWNLOAD_TIMEOUT = 7200  # 2 hours for long videos
UPLOADER_TIMEOUT = 600

# Retry Settings
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF = 2
DEFAULT_MAX_BACKOFF = 30

# Progress
UPDATE_INTERVAL = 5
MIN_UPDATE_INTERVAL = 2

# ==================== Platform Patterns ====================
PLATFORM_URLS = {
    "youtube": [
        r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|www\.youtube\.com/shorts/)",
        r"https?://youtube\.com/(?:v=|embed/|shorts/)",
    ],
    "instagram": [
        r"https?://(?:www\.)?instagram\.com/p/",
        r"https?://www\.instagram\.com/reels/",
    ],
    "twitter": [
        r"https?://(?:www\.)?twitter\.com/i/status/|https?://x\.com/i/status/",
        r"https?://twitter\.com/.*?/status/",
        r"https?://x\.com/.*?/status/",
    ],
    "reddit": [
        r"https?://(?:www\.)?reddit\.com/r/\S+/comments/\S+",
        r"https?://redd\.it/\S+",
        r"https?://v\.redd\.it/\S+",
    ],
    "facebook": [
        r"https?://(?:www\.)?facebook\.com/watch/\S+",
        r"https?://(?:www\.)?facebook\.com/reel/\S+",
        r"https?://(?:www\.)?fb\.watch/\S+",
    ],
    "linkedin": [
        r"https?://(?:www\.)?linkedin\.com/posts/\S+",
        r"https?://www\.linkedin\.com/video/watch/\S+",
    ],
}

PLATFORM_EMOJIS = {
    "youtube": "▶️",
    "instagram": "📷",
    "twitter": "✈️",
    "x": "🐦",
    "reddit": "🤖",
    "facebook": "📘",
    "linkedin": "💼",
}


# ==================== Cookie Files ====================
COOKIE_FILES = {
    "youtube": "youtube_cookies.txt",
    "instagram": "instagram_cookies.txt",
    "twitter": "twitter_cookies.txt",
    "reddit": "reddit_cookies.txt",
}


# ==================== Video Qualities ====================
QUALITIES = {
    "1080p": 1920,
    "720p": 1280,
    "480p": 854,
    "360p": 640,
    "240p": 426,
}


# ==================== Telegram File Extensions ====================
UPLOAD_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".gif", ".jpg", ".jpeg", ".png"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}


# ==================== Health Check Keys ====================
REDIS_HEALTH_KEY = "redis_ubd_health"
HEARTBEAT_KEY = f"{REDIS_HEALTH_KEY}:heartbeat"


# ==================== Aliases ====================
TWITTER_ALIAS = "x"
LINKEDIN_ALIAS = "in"


# ==================== Supported Extensions ====================
# Media for direct play on Telegram
SUPPORTED_PLAYING = {".mp4", ".m3u8", ".webm", ".mov", ".mkv", ".avi", ".m4v"}

# Media for exact file transfer
SUPPORTED_TRANSFER = {"gif", "jpeg", "jpg", "png", "mp4", "mp3", "mkv"}


# ==================== Progress Messages ====================
PROGRESS_MESSAGES = {
    "download": "📥 Downloading...",
    "process": "⚙️ Processing...",
    "upload": "📤 Uploading...",
    "success": "✅ Completed successfully!",
    "failed": "❌ Download failed",
    "cancelled": "🔄 Download cancelled",
    "queued": "⏳ Queued",
    "processing_audio": "🎵 Converting audio to mp3...",
    "extracting_thumbnail": "🖼️ Generating thumbnail...",
}


# ==================== Render-Specific ====================
# Environment variables
RENDER_ENV_KEY = "RENDER"
RENDER_REDIS_URL_KEY = "RENDER_REDIS_URL"
API_PORT = 8081
BOT_API_PORT = 8082


# ==================== Platform User-Agent Defaults ====================
USER_AGENTS = {
    "youtube": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "instagram": "Instagram/221.0.0.14.120 (iPhone14,5; iOS 16_0_1; en_US; en)",
    "twitter": "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
}


# ==================== Stream Flags ====================
# Stream copy mode (no re-encoding)
STREAM_FLAGS = {
    "video": "-c copy -bsf:v h264_mp4toannexb",
    "audio": "-c:a copy",
    "both": "-c copy -c copy -bsf:v h264_mp4toannexb",
}

# FFmpeg thumbnail flags
THUMBNAIL_FLAGS = "-vframes 1 -ss 3 -vf scale=320:-1"

# Thumbnail dimensions
THUMBNAIL_SIZE = (320, 180)


# ==================== Memory Safety ====================
FREE_MEMORY_MB_THRESHOLD = 50  # Minimum free memory before stopping
MIN_WATERMARK = (512 - 480)  # Reserve 32MB for overhead = 480MB target for file

# ==================== Auto Update ====================
YTDLP_AUTO_UPDATE_CHANNEL = "yt-dlp/yt-dlp"
UPDATE_CHECK_INTERVAL_MINUTES = 1440  # 24 hours


# ==================== Temporary Directory ====================
TEMP_DIR = "/tmp/ubd"
DOWNLOAD_DIR = "/tmp/ubd/downloads"
LOG_DIR = "/tmp/ubd/logs"

# Log settings
LOG_RETENTION_DAYS = 7

# ==================== Identifier Patterns ====================
# Media ID extraction patterns
MEDIA_ID_PATTERNS = {
    "youtube": r"v=([a-zA-Z0-9_-]{11})",
    "instagram": r"instagram\.com/p/([^/]+)",
    "twitter": r"twitter\.com/i/status/(\d+)|x\.com/i/status/(\d+)",
    "reddit": r"reddit\.com/.*?/comments/([^/]+)|redd\.it/([^/]+)",
    "facebook": r"fb\.watch/([a-zA-Z0-9_-]+)",
}

# ==================== File Size Conversion ====================
# Convert MB to bytes
MB_TO_BYTES = 1024 * 1024
KB_TO_BYTES = 1024

# Acceleration flags
# Launched with uvloop in main
USE_ULOOP = True

# ==================== Cleanup ====================
# Auto cleanup strategy (atexit + signal handlers)
AUTO_CLEANUP_MODE = "atexit"