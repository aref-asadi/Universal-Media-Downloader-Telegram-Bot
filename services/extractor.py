"""Media extraction service using yt-dlp wrapper.

This module provides the Extractor class which uses yt-dlp to extract
media info and download media from various platforms.
"""
import asyncio
import os
import re
import aiohttp
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

    async def _fetch_cobalt_instagram(self, url: str, output_dir: str) -> List[str]:
        """Fetch Instagram media via Cobalt API (handles anti-bot protections).
        
        Returns list of downloaded file paths, or empty list if failed.
        """
        cobalt_url = getattr(self.config, 'cobalt_api_url', '')
        if not cobalt_url:
            return []
        
        cobalt_key = getattr(self.config, 'cobalt_api_key', '')
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if cobalt_key:
            headers['Authorization'] = f'Apikey {cobalt_key}'
        
        payload = {
            'url': url,
            'videoQuality': '720',
            'downloadMode': 'auto',
            'alwaysProxy': True,
            'localProcessing': 'disabled',
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(cobalt_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        logger.warning(f"Cobalt API returned {resp.status}")
                        return []
                    
                    data = await resp.json()
                    logger.info(f"Cobalt response status: {data.get('status')}")
                    
                    # Parse response based on status
                    status = data.get('status')
                    media_urls = []
                    
                    if status in ('tunnel', 'redirect'):
                        media_url = data.get('url')
                        if media_url:
                            media_urls.append((media_url, data.get('filename', '')))
                    
                    elif status == 'picker':
                        picker = data.get('picker', [])
                        for item in picker:
                            if isinstance(item, dict) and item.get('url'):
                                media_urls.append((item['url'], item.get('filename', '')))
                    
                    elif status == 'local-processing':
                        # For local-processing, we get tunnel URLs
                        tunnels = data.get('tunnel', [])
                        output = data.get('output', {})
                        for tunnel_url in tunnels:
                            if tunnel_url:
                                media_urls.append((tunnel_url, output.get('filename', '')))
                    
                    if not media_urls:
                        logger.warning("Cobalt returned no media URLs")
                        return []
                    
                    # Download each media URL
                    downloaded_files = []
                    for i, (media_url, filename) in enumerate(media_urls[:10]):  # Max 10 items
                        if not filename:
                            # Generate filename from URL
                            from urllib.parse import urlparse, unquote
                            parsed = urlparse(media_url)
                            filename = unquote(parsed.path.split('/')[-1])
                            if not filename or '.' not in filename:
                                filename = f"instagram_{i+1}.mp4"
                        
                        filepath = os.path.join(output_dir, filename)
                        
                        try:
                            async with session.get(media_url) as download_resp:
                                if download_resp.status == 200:
                                    with open(filepath, 'wb') as f:
                                        async for chunk in download_resp.content.iter_chunked(8192):
                                            f.write(chunk)
                                    
                                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                                        downloaded_files.append(filepath)
                                        logger.info(f"Downloaded via Cobalt: {filename}")
                                else:
                                    logger.warning(f"Failed to download {filename}: HTTP {download_resp.status}")
                        except Exception as e:
                            logger.error(f"Download error for {filename}: {e}")
                    
                    return downloaded_files
                    
        except Exception as e:
            logger.error(f"Cobalt API error: {e}")
            return []

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
        # Use bare "best" so yt-dlp picks whatever format the item has
        # (video, image, or audio) — carousels can mix all three.
        if platform in (P.INSTAGRAM,):
            return "best"

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
            'nocheckcertificate': True,
            'retries': 3,
            'socket_timeout': 30,
            'format': self._get_format_string(platform, url),
            'outtmpl': os.path.join(output_dir, '%(title).80B [%(id)s].%(ext)s'),
            'merge_output_format': 'mp4' if not self.config.audio_only else 'm4a',
            'max_filesize': self.config.max_file_size_mb * 1024 * 1024,
            'ignoreerrors': False,
        }

        # Instagram galleries use playlist internally — allow it to download all post items
        # (photo/video carousels can have up to 10 items). Don't use playlistend.
        if platform == P.INSTAGRAM:
            options['noplaylist'] = False
        else:
            options['noplaylist'] = True

        # YouTube bot-check bypass:
        # tv_embedded works on datacenter IPs without cookies for most public videos.
        # ios is a reliable fallback. android is last resort.
        if platform == P.YOUTUBE:
            options['extractor_args'] = {
                'youtube': {
                    'player_client': ['tv_embedded', 'ios', 'android'],
                    'skip': ['hls', 'dash'],  # avoid formats that still require auth
                }
            }

        if self.config.twitter_proxy:
            options['proxy'] = self.config.twitter_proxy
        
        # Instagram: ignore errors so carousel items that fail don't kill the whole playlist
        # (image-only carousels often trigger "No video formats found" on some items)
        if platform == P.INSTAGRAM:
            options['ignoreerrors'] = True
        
        if self.config.cookies_dir:
            # Use platform-specific cookies
            from core.constants import COOKIE_FILES
            if platform and hasattr(platform, 'name'):
                platform_name = platform.name.lower()
            else:
                platform_name = str(platform).lower() if platform else 'youtube'
            
            cookie_filename = COOKIE_FILES.get(platform_name, 'youtube_cookies.txt')
            cookie_file = os.path.join(self.config.cookies_dir, cookie_filename)
            
            # Fallback to youtube cookies if platform-specific not found
            if not os.path.exists(cookie_file) and platform_name != 'youtube':
                cookie_file = os.path.join(self.config.cookies_dir, 'youtube_cookies.txt')
            
            if os.path.exists(cookie_file):
                options['cookies'] = cookie_file
        
        # Instagram extractor args - use app ID and web API for better format access
        if platform == P.INSTAGRAM:
            options['extractor_args'] = {
                'instagram': {
                    'app_id': ['936619743392459'],
                    'api-version': ['web'],
                }
            }
        
        return options

    def _resolve_filepaths(self, output_dir: str, info: dict) -> List[str]:
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
            # Last resort: newly created files (exclude temp files, keep images)
            candidates = [
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if os.path.isfile(os.path.join(output_dir, f))
                and not f.endswith(('.part', '.ytdl', '.json', '.m4a'))
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
        
        # For Instagram, try yt-dlp first, then fall back to Cobalt API
        from core.types import Platform as P
        platform, _ = get_platform_from_url(url)
        
        if platform == P.INSTAGRAM:
            try:
                result = await self._download_via_ytdlp(url, output_dir)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"yt-dlp failed for Instagram, trying Cobalt API: {e}")
            
            # Fall back to Cobalt API
            cobalt_result = await self._fetch_cobalt_instagram(url, output_dir)
            if cobalt_result:
                logger.info(f"Instagram download via Cobalt: {len(cobalt_result)} files")
                return cobalt_result
            
            raise DownloadError(
                "Instagram download failed. yt-dlp blocked by Instagram and no Cobalt API configured. "
                "Set COBALT_API_URL to enable Instagram downloads."
            )
        
        # For other platforms, use yt-dlp directly
        return await self._download_via_ytdlp(url, output_dir)

    async def _download_via_ytdlp(self, url: str, output_dir: str) -> List[str]:
        """Download using yt-dlp (blocking, run in thread)."""
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

        # Playlist/entries handling (for Instagram carousels, Reddit galleries)
        # YouTube is still noplaylist due to potential long playlist downloads.
        if 'entries' in info:
            # Only one URL was requested (`url` param), so this should be a single carousel/gallery
            # Max 10 items - Instagram carousel limit
            max_items = 10
            filepaths = set()
            entries = info.get('entries', [])
            
            for i in range(min(len(entries), max_items)):
                entry = entries[i]
                if not entry:
                    # Failed extraction (ignoreerrors=True, image-only item, etc.) - skip
                    continue
                entry_files = self._resolve_filepaths(output_dir, entry)
                filepaths.update(entry_files)
            
            if filepaths:
                return list(filepaths)
            
            # If all entries failed but we still have files in the directory, return those
            # (the download may have succeeded even if entry metadata extraction failed)
            candidate_files = [
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if os.path.isfile(os.path.join(output_dir, f))
                and not f.endswith(('.part', '.ytdl', '.json'))
            ]
            if candidate_files:
                return candidate_files

            raise DownloadError(
                "Instagram returned no downloadable items. "
                "Instagram often blocks requests from datacenter IPs — "
                "try again later or provide Instagram cookies."
            )

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