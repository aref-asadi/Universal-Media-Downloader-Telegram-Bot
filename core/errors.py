"""Custom exceptions for the Universal Media Downloader Bot."""
from typing import Optional, Any

from .types import DownloadStatus, Platform


class BaseError(Exception):
    """Base error class for the bot."""
    def __init__(self, message: str, platform: Optional[Platform] = None):
        super().__init__(message)
        self.message = message
        self.platform = platform

    def __str__(self) -> str:
        if self.platform:
            return f"[{self.platform.value.upper()} ERROR] {self.message}"
        return f"[ERROR] {self.message}"


class BotError(BaseError):
    """Base error for bot-related issues."""
    pass


class ConfigurationError(BotError):
    """Configuration-related errors."""
    pass


class RateLimitError(BotError):
    """Rate limit error."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class AuthenticationError(BotError):
    """Authentication error (e.g., invalid token, private account)."""
    pass


class NetworkError(BotError):
    """Network-related errors."""
    pass


class DownloadError(BotError):
    """Download-related errors."""
    pass


class ProcessingError(BotError):
    """Media processing errors."""
    pass


class FileSizeExceededError(ProcessingError):
    """File size exceeds limit."""
    def __init__(self, size: int, limit: int, platform: Platform = None):
        super().__init__(
            f"File size {size / 1024 / 1024:.2f}MB exceeds limit {limit / 1024 / 1024:.0f}MB",
            platform
        )
        self.size = size
        self.limit = limit


class UnsupportedTypeError(ProcessingError):
    """Unsupported media type error."""
    pass


class ExtractionError(BotError):
    """Media extraction errors."""
    pass


class UploaderError(BotError):
    """Telegram upload errors."""
    pass


class TelegramUploadError(UploaderError):
    """Telegram-specific upload errors."""
    pass


class CaptionTooLongError(BotError):
    """Caption exceeds Telegram's 4096 character limit."""
    pass


class RetryableError(BaseError):
    """Error that can be retried."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class FileNotFoundError(BotError):
    """Temporary file not found error."""
    pass


class DiskSpaceError(BotError):
    """Insufficient disk space error."""
    pass


class PytduError(ExtractionError):
    """yt-dlp specific errors."""
    def __init__(self, original_error: Any):
        message = str(original_error)
        if "is not a valid URL" in message:
            super().__init__("Invalid URL provided", None)
        elif "has been removed" in message:
            super().__init__("Content has been deleted or removed", None)
        elif "requesting from Cloudflare" in message:
            super().__init__(
                "Cloudflare challenge - check proxy/coins cookies",
                None
            )
        elif "Private video" in message:
            super().__init__(
                "Cannot play private videos - try providing cookies",
                None
            )
        else:
            super().__init__(message, None)
        self.original_error = original_error


def normalize_error(error: Exception) -> BaseError:
    """Normalize exceptions to bot-specific errors."""
    if isinstance(error, AlreadyCancelledError):
        return error
    if isinstance(error, BaseError):
        return error
    
    error_str = str(error).lower()
    
    if "timeout" in error_str or "timed out" in error_str:
        return HTTP429Error("Request timed out")
    
    if "504" in error_str or "502" in error_str or "503" in error_str:
        return DownloadError("Service unavailable, retrying...")
    
    if "rate limit" in error_str or "429" in error_str:
        return HTTP429Error("API rate limit reached")
    
    if "instruction successfully" not in error_str and "authentication failed" in error_str:
        return AuthenticationError("Authentication failed - check credentials")
    
    if "no such file" in error_str or "not found" in error_str:
        return BotError("Resource not found")
    
    if "network" in error_str or "connection" in error_str:
        return NetworkError("Network connection failed")
    
    return DownloadError(str(error))


class HTTPError(BotError):
    """HTTP errors."""
    pass


class HTTP429Error(HTTPError):
    """HTTP 429 Rate Limit."""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message)
        self.retry_after = 60


class HTTP50XError(HTTPError):
    """HTTP 5xx errors (server errors)."""
    def __init__(self, status_code: int, message: Optional[str] = None):
        super().__init__(f"Server error {status_code}: {message or 'Service unavailable'}")
        self.status_code = status_code


class AlreadyCancelledError(BotError):
    """Operation was cancelled by user."""
    pass


class GameError(BotError):
    """Game state errors (e.g., task doesn't exist)."""
    def __init__(self, message: str):
        super().__init__(message)


class NotFoundError(BotError):
    """Resource not found."""
    pass