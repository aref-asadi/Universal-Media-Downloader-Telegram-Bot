"""Ephemeral file cleanup utilities for Render's temporary storage."""
import atexit
import os
import sys
import signal
import time
from pathlib import Path
from typing import Optional

from core.constants import TEMP_DIR, DOWNLOAD_DIR, LOG_DIR, LOG_RETENTION_DAYS
from utils.logger import logger


class TempDirManager:
    """Manages temporary directories and ephemeral file cleanup."""

    def __init__(self, temp_dir: str = TEMP_DIR):
        self.temp_dir = temp_dir
        self._cleanup_handlers = []

    def setup_temp_dirs(self) -> None:
        """Create required temporary directories."""
        try:
            Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
            Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
            Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
            logger.info(f"Temp directories setup: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to setup temp dirs: {e}")
            self.temp_dir = os.getcwd()
            Path(self.temp_dir).mkdir(parents=True, exist_ok=True)

    def create_job_dir(self) -> str:
        """Create a unique temporary directory for a job."""
        job_id = f"{int(time.time() * 1000)}_{os.getpid()}"
        job_path = os.path.join(self.temp_dir, job_id)
        os.makedirs(job_path, exist_ok=True)
        return job_path

    def create_subdir(self, job_dir: str, name: str) -> str:
        """Create a subdirectory within a job directory."""
        subdir = os.path.join(job_dir, name)
        os.makedirs(subdir, exist_ok=True)
        return subdir

    def add_cleanup_handler(self, cleanup_func: callable) -> None:
        """Register a cleanup function to be executed on exit."""
        self._cleanup_handlers.append(cleanup_func)
        return cleanup_func

    def _execute_cleanup_handlers(self) -> None:
        """Execute all registered cleanup handlers."""
        errors = []
        for i, handler in enumerate(self._cleanup_handlers):
            try:
                logger.debug(f"Running cleanup handler {i + 1}/{len(self._cleanup_handlers)}")
                handler()
            except Exception as e:
                errors.append(str(e))
                logger.error(f"Cleanup handler {i + 1} failed: {e}")
        if errors:
            logger.warning(f"Cleanup completed with {len(errors)} errors: {errors}")

    def get_temp_dir(self) -> str:
        """Get the configured temporary directory."""
        return self.temp_dir

    def force_delete(self, path: str) -> bool:
        """Force delete a file or directory inside the temp tree."""
        return AUTO_CLEANUP.force_delete(path)


TEMP_MANAGER = TempDirManager()


class AutoCleanup:
    """Automatic cleanup with multiple cleanup strategies."""

    def __init__(self):
        self._registered = False
        self._cleaned = False

    def register_all(self) -> None:
        """Register all cleanup strategies."""
        if self._registered:
            return
        atexit.register(self._cleanup_at_exit)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        self._registered = True
        logger.info("Cleanup handlers registered")

    def _cleanup_at_exit(self) -> None:
        """Cleanup on normal exit (idempotent)."""
        if self._cleaned:
            return
        self._cleaned = True
        logger.info("Running cleanup on exit")
        TEMP_MANAGER._execute_cleanup_handlers()

    def _signal_handler(self, signum, frame) -> None:
        """Handler for signals to ensure cleanup."""
        logger.info(f"Signal {signum} received, cleaning up...")
        TEMP_MANAGER._execute_cleanup_handlers()
        sys.exit(0)

    def force_delete(self, path: str) -> bool:
        """Force delete a file or directory."""
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                if path.startswith(TEMP_MANAGER.temp_dir):
                    for root, dirs, files in os.walk(path, topdown=False):
                        for name in files:
                            os.remove(os.path.join(root, name))
                        for name in dirs:
                            os.rmdir(os.path.join(root, name))
                    os.rmdir(path)
                else:
                    logger.warning(f"Skipping deletion of path outside temp: {path}")
                    return False
            return True
        except FileNotFoundError:
            return True
        except Exception:
            logger.error(f"Failed to delete {path}")
            return False


AUTO_CLEANUP = AutoCleanup()
AUTO_CLEANUP.register_all()


def delete_file(path: str, attempt: int = 1, max_attempts: int = 3) -> bool:
    """Delete a file with retry logic."""
    try:
        if os.path.exists(path):
            os.remove(path)
        return True
    except Exception:
        if attempt < max_attempts:
            time.sleep(min(0.1 * attempt, 1.0))
            return delete_file(path, attempt + 1, max_attempts)
        logger.error(f"Failed to delete file after {max_attempts} attempts: {path}")
        return False


def get_files_in_temp_dir(pattern: Optional[str] = None) -> list:
    """Get list of files/directories in temp directory."""
    try:
        if not os.path.exists(TEMP_MANAGER.temp_dir):
            return []
        if pattern:
            return [os.path.join(TEMP_MANAGER.temp_dir, p) for p in os.listdir(TEMP_MANAGER.temp_dir) if pattern in p]
        return [os.path.join(TEMP_MANAGER.temp_dir, p) for p in os.listdir(TEMP_MANAGER.temp_dir)]
    except Exception:
        return []


def get_disk_usage_mb(path: str = TEMP_MANAGER.temp_dir) -> int:
    """Get disk usage in megabytes."""
    try:
        total = 0
        for root, _, files in os.walk(path):
            for file in files:
                try:
                    total += os.path.getsize(os.path.join(root, file))
                except:
                    pass
        return total // (1024 * 1024)
    except Exception:
        return 0