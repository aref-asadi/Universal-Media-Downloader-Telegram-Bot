"""Utils module for the Universal Media Downloader Bot."""
from .logger import logger, get_logger, Logger, LogSettings
from .mb_convert import (
    bytes_to_mb,
    mb_to_bytes,
    format_file_size,
    get_approximate_bitrate,
    estimate_video_duration,
    get_quality_from_size,
    bytes_to_human,
    trim_file_size_to_limit,
)

__all__ = [
    "Logger",
    "LogSettings",
    "logger",
    "get_logger",
    "bytes_to_mb",
    "mb_to_bytes",
    "format_file_size",
    "get_approximate_bitrate",
    "estimate_video_duration",
    "get_quality_from_size",
    "bytes_to_human",
    "trim_file_size_to_limit",
]