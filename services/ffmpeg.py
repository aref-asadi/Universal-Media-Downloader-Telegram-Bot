"""FFmpeg processor for media operations."""
import asyncio
import os
import subprocess
from typing import Optional, Tuple

from core.errors import ProcessingError
from utils.logger import logger


class FFmpegProcessor:
    """FFmpeg wrapper for media processing."""
    
    def __init__(self):
        self._available = None
    
    @property
    def is_available(self) -> bool:
        if self._available is None:
            try:
                result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
                self._available = result.returncode == 0
            except:
                self._available = False
        return self._available
    
    async def extract_thumbnail(self, video_path: str, output_path: str) -> str:
        """Extract thumbnail from video."""
        if not self.is_available:
            raise ProcessingError("FFmpeg not available")
        cmd = ["ffmpeg", "-v", "error", "-ss", "0", "-i", video_path, "-frames:v", "1", "-vf", "scale=320:-1", "-y", output_path]
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise ProcessingError(f"Thumbnail failed: {stderr.decode()}")
            return output_path if os.path.exists(output_path) else (_ for _ in ()).throw(ProcessingError("No thumbnail"))
        except FileNotFoundError:
            raise ProcessingError("FFmpeg not found")
        except Exception as e:
            raise ProcessingError(f"Thumbnail error: {e}")

    async def merge_audio_video(self, video_path: str, audio_path: str, output_path: str) -> str:
        """Merge video and audio using stream copy."""
        if not self.is_available:
            raise ProcessingError("FFmpeg not available")
        if audio_path == video_path:
            return video_path
        cmd = ["ffmpeg", "-i", video_path, "-i", audio_path, "-c", "copy", "-c:a", "copy", "-y", output_path]
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise ProcessingError(f"Merge failed: {stderr.decode()}")
            return output_path if os.path.exists(output_path) else (_ for _ in ()).throw(ProcessingError("No merged file"))
        except FileNotFoundError:
            raise ProcessingError("FFmpeg not found")
        except Exception:
            raise ProcessingError("Merge failed")

    async def get_duration(self, media_path: str) -> int:
        """Get duration in seconds."""
        if not os.path.exists(media_path):
            raise FileNotFoundError(f"File not found: {media_path}")
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", media_path]
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await proc.communicate()
            if proc.returncode != 0:
                return 60
            return max(1, int(float(stdout.decode().strip())))
        except:
            return 60
    
    async def validate_file(self, file_path: str, max_mb: int = 512) -> Tuple[bool, str]:
        if not os.path.exists(file_path):
            return False, "File not found"
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > max_mb:
            return False, f"Too large: {size_mb:.2f}MB > {max_mb}MB"
        return True, ""


ffmpeg_processor = FFmpegProcessor()