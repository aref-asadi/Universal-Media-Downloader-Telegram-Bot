"""Media extraction service using yt-dlp wrapper."""
import asyncio
import os
from typing import Optional, List, Dict

import yt_dlp
import yt_dlp.utils

from core.types import Platform, MediaType, MediaInfo, VideoQuality
from core.errors import PytduError, AuthenticationError, DownloadError, normalize_error
from core.dia_config import get_platform_from_url, get_platform_config
from utils.logger import logger


class Extractor:
    """Media extractor using yt-dlp."""

    def __init__(self, config):
        self.config = config
        self._yt_dlp_instance: Optional['yt_dlp.YoutubeDL'] = None

    @property
    def _yt_dlp(self) -> 'yt_dlp.YoutubeDL':
        if self._yt_dlp_instance is None:
            self._yt_dlp_instance = self._create_yt_dlp()
        return self._yt_dlp_instance

    def _create_yt_dlp(self) -> 'yt_dlp.YoutubeDL':
        """Create a yt-dlp instance with appropriate options."""
        options = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'prefer_insecure': True,
        }

        if self.config.twitter_proxy:
            options['proxy'] = self.config.twitter_proxy

        if self.config.cookies_dir:
            cookie_file = os.path.join(self.config.cookies_dir, "youtube_cookies.txt")
            if os.path.exists(cookie_file):
                options['cookies'] = cookie_file

        return yt_dlp.YoutubeDL(options)

    async def extract_media_info(self, url: str) -> MediaInfo:
        """Extract media information from URL."""
        try:
            platform, _ = get_platform_from_url(url)
            config = get_platform_config(platform, self.config.cookies_dir)

            info = self._yt_dlp.extract_info(url, download=False)
            return self._parse_media_info(platform, info)
        except yt_dlp.utils.ExtractorError as e:
            raise PytduError(e)
        except Exception as e:
            raise PytduError(e)

    def _parse_media_info(self, platform: Platform, info: dict) -> MediaInfo:
        """Parse media information from yt-dlp output."""
        try:
            media_type = MediaType.VIDEO
            if info.get('acodec') != 'none' and info.get('vcodec') == 'none':
                media_type = MediaType.AUDIO
            elif not info.get('duration') and not info.get('width'):
                media_type = MediaType.IMAGE

            return MediaInfo(
                platform=platform,
                media_type=media_type,
                title=info.get('title', info.get('webpage_url', 'Untitled')),
                author=info.get('uploader', 'Unknown'),
                url=info.get('webpage_url', ''),
                thumbnail=info.get('thumbnail'),
                description=info.get('description', ''),
                duration=info.get('duration'),
            )
        except Exception:
            return MediaInfo(
                platform=platform,
                media_type=MediaType.VIDEO,
                title=info.get('title', 'Unknown'),
                author='Unknown',
                url='',
            )

    def _get_format_string(self, platform: 'Platform', url: str) -> str:
        """Build format string based on quality settings and platform capabilities."""
        from core.types import Platform as P
        quality = self.config.video_quality
        audio_only = self.config.audio_only

        if audio_only:
            return "bestaudio/best"

        # Height cap from quality setting
        h = {"1080p": 1080, "720p": 720, "480p": 480, "360p": 360}.get(quality, 720)

        # Instagram only has pre-muxed streams — asking for separate video+audio
        # streams always fails with "Requested format is not available".
        if platform in (P.INSTAGRAM,):
            return f"best[height<={h}]/best"

        # Universal: prefer separate streams (better quality), fall back to
        # muxed if the platform doesn't offer them (Twitter, Reddit, Facebook).
        return (
            f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]"
            f"/bestvideo[height<={h}]+bestaudio"
            f"/best[height<={h}]"
            f"/best"
        )

    def _cleanup_other_files(self, output_dir: str, media_id: str, kept_ext: str) -> None:
        """Remove other format files for the same media."""
        for file in os.listdir(output_dir):
            if file.startswith(f"{media_id}."):
                ext = file.split('.')[-1]
                if ext != kept_ext and ext not in ('jpg', 'png'):
                    try:
                        os.remove(os.path.join(output_dir, file))
                    except:
                        pass

    def _build_download_options(self, output_dir: str, url: str = '') -> dict:
        """Build yt-dlp options for a download."""
        from core.dia_config import get_platform_from_url
        from core.types import Platform as P

        platform, _ = get_platform_from_url(url) if url else (None, None)

        options = {
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'retries': 3,
            'socket_timeout': 30,
            'format': self._get_format_string(platform, url),
            'outtmpl': os.path.join(output_dir, '%(title).80B [%(id)s].%(ext)s'),
            'merge_output_format': 'mp4' if not self.config.audio_only else 'm4a',
            'max_filesize': self.config.max_file_size_mb * 1024 * 1024,
            'ignoreerrors': False,
        }

        # YouTube bot-check bypass: use Android client which doesn't require login
        if platform == P.YOUTUBE:
            options['extractor_args'] = {'youtube': {'player_client': ['android']}}

        if self.config.twitter_proxy:
            options['proxy'] = self.config.twitter_proxy
        if self.config.cookies_dir:
            cookie_file = os.path.join(self.config.cookies_dir, "youtube_cookies.txt")
            if os.path.exists(cookie_file):
                options['cookies'] = cookie_file
        return options

    @staticmethod
    def _resolve_filepaths(output_dir: str, info: dict) -> List[str]:
        """Resolve final file paths from yt-dlp info dict."""
        paths: List[str] = []
        requested = info.get('requested_downloads') or []
        for entry in requested:
            fp = entry.get('filepath')
            if fp and os.path.exists(fp):
                paths.append(fp)
        if paths:
            return paths

        # Fallback: prepared filename (may differ after merge)
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                prepared = ydl.prepare_filename(info)
            if os.path.exists(prepared):
                paths.append(prepared)
        except Exception:
            pass

        if not paths:
            # Last resort: newest file in output dir
            candidates = [
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if os.path.isfile(os.path.join(output_dir, f))
                and not f.endswith(('.part', '.ytdl', '.json', '.jpg', '.png', '.webp'))
            ]
            candidates.sort(key=os.path.getmtime, reverse=True)
            paths = candidates[:1]
        return paths

    async def download_media(self, url: str, output_dir: str) -> List[str]:
        """Download media from URL into output_dir.

        Runs the blocking yt-dlp download in a worker thread so the event
        loop stays responsive on the 512MB Render instance.

        Returns:
            List of downloaded file paths (single item for regular videos).
        """
        os.makedirs(output_dir, exist_ok=True)
        options = self._build_download_options(output_dir, url)

        def _run() -> dict:
            with yt_dlp.YoutubeDL(options) as ydl:
                return ydl.extract_info(url, download=True)

        try:
            info = await asyncio.to_thread(_run)
        except yt_dlp.utils.DownloadError as e:
            raise PytduError(e)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise DownloadError(normalize_error(e).message)

        if info is None:
            raise DownloadError("yt-dlp returned no data")

        # Playlist/nested entries (shouldn't happen with noplaylist, but be safe)
        if 'entries' in info:
            entries = [e for e in info['entries'] if e]
            if not entries:
                raise DownloadError("No downloadable entries found")
            info = entries[0]

        filepaths = self._resolve_filepaths(output_dir, info)
        if not filepaths:
            raise DownloadError("Download finished but no file was produced")

        logger.info(f"Downloaded {len(filepaths)} file(s): {filepaths[0]}")
        return filepaths


class TwitterExtractor(Extractor):
    """Special handling for Twitter/X media extraction."""
    def _parse_media_info(self, platform: Platform, info: dict) -> MediaInfo:
        """Parse Twitter-specific media info."""
        extended_entities = info.get('ext', {}).get('media', [])
        if extended_entities and extended_entities[0].get('type') == 'video':
            return MediaInfo(
                platform=platform,
                media_type=MediaType.VIDEO,
                title=info.get('title', info.get('description', 'Twitter Video')),
                author=info.get('uploader', '@' + str(info.get('id', 'unknown'))),
                url=info.get('webpage_url', ''),
            )
        return super()._parse_media_info(platform, info)


class RedditExtractor(Extractor):
    """Special handling for Reddit media extraction."""
    def _parse_media_info(self, platform: Platform, info: dict) -> MediaInfo:
        """Parse Reddit-specific media info."""
        if 'entries' in info:
            return MediaInfo(
                platform=platform,
                media_type=MediaType.GALLERY,
                title=info['entries'][0].get('title', info['entries'][0].get('display_name', 'Reddit Gallery')),
                author=info['entries'][0].get('subreddit', ''),
                url=info.get('webpage_url', ''),
            )
        return super()._parse_media_info(platform, info)


def create_extractor(config) -> Extractor:
    """Factory: pick an extractor implementation for the platform config."""
    # Platform-specific subclasses currently only override info parsing;
    # download logic is shared, so the base extractor covers all platforms.
    return Extractor(config)