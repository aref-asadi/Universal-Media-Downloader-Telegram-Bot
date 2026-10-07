"""Storage module for the Universal Media Downloader Bot."""
from .cleanup import (
    TEMP_DIR,
    TEMP_MANAGER,
    TempDirManager,
    AutoCleanup,
    AUTO_CLEANUP,
    delete_file,
    get_files_in_temp_dir,
    get_disk_usage_mb,
)

__all__ = [
    "TempDirManager",
    "TEMP_DIR",
    "TEMP_MANAGER",
    "AutoCleanup",
    "AUTO_CLEANUP",
    "delete_file",
    "get_files_in_temp_dir",
    "get_disk_usage_mb",
]