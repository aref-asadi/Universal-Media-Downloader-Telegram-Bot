"""Logging utilities with memory-safe configuration."""
import os
import sys
from pathlib import Path
from typing import List, Optional

from loguru import logger as _logger
from pydantic import field_validator
from pydantic_settings import BaseSettings


class LogSettings(BaseSettings):
    """Logging configuration."""
    debug: bool = False
    log_level: str = "INFO"
    log_format: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    log_retention_days: int = 7
    log_rotation: str = "00:00"  # Daily rotation
    disable_stdout: bool = False

    @field_validator("debug", "disable_stdout", mode="before")
    @classmethod
    def _coerce_bool(cls, v):
        """Tolerate non-boolean DEBUG-style env vars (e.g. DEBUG=WARN)."""
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return bool(v)


class Logger:
    """Logger singleton with memory-safe initialization."""
    
    _instance: Optional['Logger'] = None
    _is_initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, settings: Optional[LogSettings] = None) -> None:
        """Initialize logger."""
        if self._is_initialized:
            return
        
        if settings is None:
            settings = LogSettings()
        
        # Remove default handler
        _logger.remove()
        
        # Console handler (stdout/stderr is the log stream on Render)
        if not settings.disable_stdout:
            _logger.add(
                sys.stderr,
                format=settings.log_format,
                level=settings.log_level,
                colorize=True,
                backtrace=settings.debug,
                diagnose=settings.debug,
            )
        
        # File handler (memory-aware)
        _logger.add(
            self._get_log_file_path(),
            format=settings.log_format,
            level=settings.log_level,
            rotation=settings.log_rotation,
            retention=f"{settings.log_retention_days} days",
            encoding="utf-8",
            compression="zip",
        )
        
        # Error-only handler
        _logger.add(
            self._get_log_file_path(".errors"),
            format=settings.log_format,
            level="ERROR",
            rotation=settings.log_rotation,
            retention="30 days",
            encoding="utf-8",
            compression="zip",
        )
        
        self._is_initialized = True
        
        if settings.debug:
            _logger.info("Logger initialized with debug mode")
    
    def _get_log_file_path(self, suffix: str = "") -> str:
        """Get log file path."""
        try:
            # Use temp directory on Render, or logs folder locally
            if "RENDER" in os.environ:
                log_dir = os.environ.get("TEMP", "/tmp")
            else:
                log_dir = os.path.join(os.getcwd(), "logs")
            
            Path(log_dir).mkdir(parents=True, exist_ok=True)
            
            timestamp = ""
            if suffix:
                timestamp = f"_{suffix}"
            
            return os.path.join(log_dir, f"ubd{timestamp}.log")
        except Exception as e:
            # Fallback to working directory
            return os.path.join(os.getcwd(), f"ubd{suffix}.log")
    
    def __getattr__(self, name: str):
        """Delegate any logger method/attribute (info, error, log, ...) to loguru."""
        return getattr(self.logger, name)
    
    def __call__(self, *args, **kwargs):
        """Allow logger(...) as a callable."""
        return self.logger(*args, **kwargs)
    
    @property
    def logger(self):
        """Get the loguru logger instance."""
        if not self._is_initialized:
            self.initialize()
        return _logger


def _is_error_filter(record):
    """Filter to show only errors and above."""
    return record["level"].name == "ERROR"


# Global instances
logger = Logger()


def get_logger(name: str):
    """Get a named logger."""
    return logger.logger.bind(name=name)