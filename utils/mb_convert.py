"""Byte and memory size conversion utilities."""
from typing import Optional
from math import log


def bytes_to_mb(bytes_value: int) -> float:
    """Convert bytes to megabytes."""
    return bytes_value / 1024 / 1024


def mb_to_bytes(mb_value: float) -> int:
    """Convert megabytes to bytes."""
    return int(mb_value * 1024 * 1024)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Examples:
        1024 -> 1 KB
        1024 * 1024 -> 1 MB
        1024 * 1024 * 1024 -> 1 GB
    """
    try:
        for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    except:
        return "0 B"


def get_approximate_bitrate(duration_seconds: int, target_size_mb: int) -> int:
    """
    Calculate approximate bitrate based on target size and duration.
    
    Bitrate (kbps) ≈ (Target Size in MB * 8 * 1000) / Duration in seconds
    """
    if duration_seconds <= 0:
        return 0
    
    target_size_bytes = target_size_mb * 1024 * 1024
    bitrate_kbps = (target_size_bytes * 8) / duration_seconds
    return int(bitrate_kbps)


def estimate_video_duration(file_size_mb: int, average_bitrate_kbps: int) -> Optional[int]:
    """
    Estimate video duration from file size and bitrate.
    
    Duration (seconds) ≈ (Size in MB * 1024 * 1024) / (Bitrate in kbps * 1000)
    """
    try:
        if average_bitrate_kbps <= 0:
            return 60  # Default to 1 minute if bitrate unknown
        
        file_size_bytes = file_size_mb * 1024 * 1024
        duration_seconds = file_size_bytes / (average_bitrate_kbps * 1000 / 8)
        
        return max(1, int(duration_seconds))
    except Exception:
        return 60


def get_quality_from_size(file_size_mb: int, config_mb: int) -> str:
    """
    Get quality setting based on file size.
    
    Returns:
        720p, 480p, or 360p based on file size relative to target
    """
    if file_size_mb > config_mb:  # reduce resolution for large files
        return "480p"
    if file_size_mb > config_mb * 0.5:
        return "720p"
    return "auto"


def bytes_to_human(bytes_val: int, use_bits: bool = False) -> str:
    """Convert bytes to human-readable with bits or bytes suffix."""
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    factor = 8 if use_bits else 1
    
    for unit in units:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val / 1024.0 * factor:.2f} {unit}"
        bytes_val /= 1024.0
    
    return f"{bytes_val / 1024.0 * factor:.2f} PB"


def format_percentage(current: int, total: int) -> float:
    """Format current/total as percentage."""
    if total <= 0:
        return 0.0
    return (current / total) * 100


def is_file_size_within_limit(file_size_bytes: int, max_size_mb: int) -> bool:
    """Check if file size is within limit."""
    return file_size_bytes <= max_size_mb * 1024 * 1024


def get_downgrade_quality(current_mb: int, target_mb: int) -> Optional[str]:
    """
    Get next lower quality for downgrading due to size.
    
    Returns:
        720p if current > target * 1.2
        480p if current > target * 2.0
        360p if current > target * 3.0
    """
    threshold_720p = target_mb * 1.2
    threshold_480p = target_mb * 2.0
    threshold_360p = target_mb * 3.0
    
    if current_mb > threshold_720p:
        return "480p"
    if current_mb > threshold_480p:
        return "720p"
    if current_mb > threshold_360p:
        return "360p"
    return None


def trim_file_size_to_limit(file_size_bytes: int, max_size_mb: int) -> int:
    """Trim file size to limit (not recommended, use downgrading instead)."""
    return min(file_size_bytes, max_size_mb * 1024 * 1024)