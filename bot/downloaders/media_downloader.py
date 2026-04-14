"""Unified media downloader using yt-dlp for all platforms.

Primary engine: yt-dlp
Fallback: BeautifulSoup scraper for direct media URL extraction
Features: proxy rotation, user-agent spoofing, async download queue
"""

import os
import asyncio
import shutil
from pathlib import Path
from typing import Any

import requests
import yt_dlp

from bot.config import (
    AUDIO_FORMAT,
    AUDIO_QUALITY,
    BROWSER_COOKIES_ENABLED,
    COOKIES_FILE,
    DOWNLOAD_DIR,
    DOWNLOAD_TIMEOUT,
    FALLBACK_SCRAPER_ENABLED,
    MAX_FILE_SIZE,
    POT_SERVER_URL,
    PROXY_FILE,
    VIDEO_QUALITIES,
)
from bot.downloaders.browser_cookies import extract_youtube_cookies_sync, get_cached_cookie_path
from bot.downloaders.fallback_scraper import scrape_media_urls
from bot.utils.helpers import sanitize_filename
from bot.utils.logger import logger
from bot.utils.proxy_manager import (
    get_yt_dlp_proxy_opts,
    load_proxies_from_file,
    report_proxy_failure,
    report_proxy_success,
)


class DownloadResult:
    """Result of a download operation."""

    def __init__(
        self,
        success: bool,
        file_path: str | None = None,
        title: str = "",
        duration: int = 0,
        file_size: int = 0,
        thumbnail: str | None = None,
        error: str | None = None,
        media_type: str = "video",
    ):
        self.success = success
        self.file_path = file_path
        self.title = title
        self.duration = duration
        self.file_size = file_size
        self.thumbnail = thumbnail
        self.error = error
        self.media_type = media_type


class MediaDownloader:
    """Download media from various platforms using yt-dlp."""

    def __init__(self) -> None:
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self._node_path = shutil.which("node")
        # Load proxies from file if configured
        if PROXY_FILE and os.path.exists(PROXY_FILE):
            load_proxies_from_file(PROXY_FILE)

    def _get_base_opts(self) -> dict[str, Any]:
        """Get base yt-dlp options."""
        # Get rotating user-agent and optional proxy
        proxy_opts = get_yt_dlp_proxy_opts()

        opts: dict[str, Any] = {
            "noplaylist": True,
            "no_warnings": True,
            "quiet": True,
            "no_color": True,
            "socket_timeout": 30,
            "retries": 3,
            "fragment_retries": 3,
        }
        # Merge proxy/UA opts (http_headers, proxy)
        opts.update(proxy_opts)

        # Add cookies file if configured (manual takes priority)
        if COOKIES_FILE and os.path.exists(COOKIES_FILE):
            opts["cookiefile"] = COOKIES_FILE
        elif BROWSER_COOKIES_ENABLED:
            # Use browser-extracted cookies if available
            cached = get_cached_cookie_path()
            if cached:
                opts["cookiefile"] = cached

        return opts

    def _get_youtube_opts(self) -> dict[str, Any]:
        """Get YouTube-specific yt-dlp options for bot detection bypass."""
        opts: dict[str, Any] = {}
        extractor_args: list[str] = []

        # Configure PO Token server if available
        if POT_SERVER_URL:
            extractor_args.append(f"getpot_bgutil_baseurl={POT_SERVER_URL}")

        if extractor_args:
            opts["extractor_args"] = {"youtube": extractor_args}

        return opts

    @staticmethod
    def _is_youtube_url(url: str) -> bool:
        """Check if a URL is a YouTube URL."""
        youtube_domains = ["youtube.com", "youtu.be"]
        return any(domain in url.lower() for domain in youtube_domains)

    async def get_info(self, url: str) -> dict[str, Any] | None:
        """Get media information without downloading."""
        opts = self._get_base_opts()
        opts["skip_download"] = True

        if self._is_youtube_url(url):
            opts.update(self._get_youtube_opts())

        try:
            info = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self._extract_info, url, opts
                ),
                timeout=60,
            )
            return info
        except asyncio.TimeoutError:
            logger.error("Timeout getting info for %s", url)
            return None
        except Exception as e:
            logger.error("Error getting info for %s: %s", url, e)
            return None

    def _extract_info(self, url: str, opts: dict[str, Any]) -> dict[str, Any] | None:
        """Extract info synchronously."""
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def download_video(
        self, url: str, quality: str = "best", user_id: int = 0
    ) -> DownloadResult:
        """Download a video from a URL."""
        output_template = str(
            DOWNLOAD_DIR / f"{user_id}_%(id)s_video.%(ext)s"
        )

        format_str = VIDEO_QUALITIES.get(quality, VIDEO_QUALITIES["best"])

        opts = self._get_base_opts()
        opts.update(
            {
                "format": format_str,
                "outtmpl": output_template,
                "merge_output_format": "mp4",
                "postprocessors": [
                    {
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": "mp4",
                    }
                ],
            }
        )

        if self._is_youtube_url(url):
            opts.update(self._get_youtube_opts())

        return await self._execute_download(url, opts, "video", user_id)

    async def download_audio(self, url: str, user_id: int = 0) -> DownloadResult:
        """Download audio (MP3) from a URL."""
        output_template = str(
            DOWNLOAD_DIR / f"{user_id}_%(id)s_audio.%(ext)s"
        )

        opts = self._get_base_opts()
        opts.update(
            {
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": AUDIO_FORMAT,
                        "preferredquality": AUDIO_QUALITY,
                    }
                ],
            }
        )

        if self._is_youtube_url(url):
            opts.update(self._get_youtube_opts())

        return await self._execute_download(url, opts, "audio", user_id)

    async def download_thumbnail(self, url: str, user_id: int = 0) -> DownloadResult:
        """Download the thumbnail/image from a URL."""
        output_template = str(
            DOWNLOAD_DIR / f"{user_id}_%(id)s_thumb.%(ext)s"
        )

        opts = self._get_base_opts()
        opts.update(
            {
                "skip_download": True,
                "writethumbnail": True,
                "outtmpl": output_template,
                "postprocessors": [
                    {
                        "key": "FFmpegThumbnailsConvertor",
                        "format": "jpg",
                    }
                ],
            }
        )

        if self._is_youtube_url(url):
            opts.update(self._get_youtube_opts())

        return await self._execute_download(url, opts, "photo", user_id)

    async def _execute_download(
        self, url: str, opts: dict[str, Any], media_type: str, user_id: int = 0
    ) -> DownloadResult:
        """Execute the download with timeout and fallback scraper."""
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self._sync_download, url, opts, media_type
                ),
                timeout=DOWNLOAD_TIMEOUT,
            )

            # If yt-dlp failed, try fallback scraper
            if not result.success and FALLBACK_SCRAPER_ENABLED:
                logger.info("yt-dlp failed for %s, trying fallback scraper", url)
                fallback = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, self._fallback_download, url, media_type, user_id
                    ),
                    timeout=DOWNLOAD_TIMEOUT,
                )
                if fallback.success:
                    return fallback

            return result
        except asyncio.TimeoutError:
            logger.error("Download timeout for %s", url)
            return DownloadResult(
                success=False,
                error="Download timed out. The file may be too large.",
                media_type=media_type,
            )
        except Exception as e:
            logger.error("Download error for %s: %s", url, e)
            return DownloadResult(
                success=False,
                error=f"Download failed: {str(e)[:200]}",
                media_type=media_type,
            )

    def _sync_download(
        self, url: str, opts: dict[str, Any], media_type: str
    ) -> DownloadResult:
        """Perform synchronous download."""
        downloaded_file: str | None = None

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    return DownloadResult(
                        success=False,
                        error="Could not extract media information.",
                        media_type=media_type,
                    )

                title = info.get("title", "Unknown")
                duration = info.get("duration", 0) or 0
                thumbnail = info.get("thumbnail")

                if media_type == "photo":
                    # For thumbnails, find the downloaded image file
                    base = opts["outtmpl"].replace("%(id)s", info.get("id", "unknown")).replace("%(ext)s", "jpg")
                    if os.path.exists(base):
                        downloaded_file = base
                    else:
                        # Search for any matching thumbnail file
                        dl_dir = DOWNLOAD_DIR
                        media_id = info.get("id", "")
                        for f in dl_dir.iterdir():
                            if media_id and media_id in f.name and f.suffix in (".jpg", ".png", ".webp"):
                                downloaded_file = str(f)
                                break
                else:
                    # For video/audio, get the prepared filename
                    requested_downloads = info.get("requested_downloads")
                    if requested_downloads:
                        downloaded_file = requested_downloads[0].get("filepath")
                    if not downloaded_file:
                        # Fallback: search download dir
                        media_id = info.get("id", "")
                        for f in DOWNLOAD_DIR.iterdir():
                            if media_id and media_id in f.name:
                                downloaded_file = str(f)
                                break

                if not downloaded_file or not os.path.exists(downloaded_file):
                    return DownloadResult(
                        success=False,
                        error="Download completed but file not found.",
                        media_type=media_type,
                    )

                file_size = os.path.getsize(downloaded_file)

                if file_size > MAX_FILE_SIZE:
                    os.remove(downloaded_file)
                    return DownloadResult(
                        success=False,
                        error=(
                            f"File is too large ({file_size / (1024*1024):.1f} MB). "
                            f"Telegram limit is {MAX_FILE_SIZE / (1024*1024):.0f} MB. "
                            "Try a lower quality."
                        ),
                        media_type=media_type,
                    )

                return DownloadResult(
                    success=True,
                    file_path=downloaded_file,
                    title=sanitize_filename(title),
                    duration=int(duration),
                    file_size=file_size,
                    thumbnail=thumbnail,
                    media_type=media_type,
                )

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "is not a valid URL" in error_msg:
                return DownloadResult(
                    success=False,
                    error="Invalid URL. Please send a valid link.",
                    media_type=media_type,
                )
            if "Private video" in error_msg or "private" in error_msg.lower():
                return DownloadResult(
                    success=False,
                    error="This content is private and cannot be downloaded.",
                    media_type=media_type,
                )
            if "unavailable" in error_msg.lower() or "not available" in error_msg.lower():
                return DownloadResult(
                    success=False,
                    error="This content is unavailable or has been removed.",
                    media_type=media_type,
                )
            # YouTube bot detection - try browser cookie extraction
            if "Sign in to confirm" in error_msg or "confirm you're not a bot" in error_msg:
                if BROWSER_COOKIES_ENABLED and not opts.get("_browser_cookies_attempted"):
                    logger.info("YouTube bot detection triggered — attempting browser cookie extraction")
                    cookie_path = extract_youtube_cookies_sync()
                    if cookie_path:
                        opts["cookiefile"] = cookie_path
                        opts["_browser_cookies_attempted"] = True
                        return self._sync_download(url, opts, media_type)
                return DownloadResult(
                    success=False,
                    error=(
                        "\u26a0\ufe0f YouTube requires authentication from this server.\n\n"
                        "Browser cookie extraction was attempted but YouTube "
                        "still blocked the request.\n\n"
                        "The bot owner can provide a cookies.txt file "
                        "from a logged-in browser to enable YouTube downloads.\n\n"
                        "Other platforms (TikTok, Instagram, etc.) work normally!"
                    ),
                    media_type=media_type,
                )
            # Age-restricted content
            if "age" in error_msg.lower() and (
                "restrict" in error_msg.lower() or "gate" in error_msg.lower()
            ):
                return DownloadResult(
                    success=False,
                    error=(
                        "This content is age-restricted. "
                        "A cookies.txt file with a logged-in account is needed."
                    ),
                    media_type=media_type,
                )
            return DownloadResult(
                success=False,
                error=f"Download error: {error_msg[:200]}",
                media_type=media_type,
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                error=f"Unexpected error: {str(e)[:200]}",
                media_type=media_type,
            )

    def _fallback_download(
        self, url: str, media_type: str, user_id: int = 0
    ) -> DownloadResult:
        """Fallback: scrape page for direct media URLs using BeautifulSoup.

        Called when yt-dlp fails. Attempts to find direct mp4/m4a/webm
        URLs in the page HTML via <video>, <source>, OG tags, and scripts.
        """
        logger.info("Attempting fallback scraper for %s", url)

        scraped = scrape_media_urls(url)
        if not scraped:
            return DownloadResult(
                success=False,
                error="Fallback scraper found no media on this page.",
                media_type=media_type,
            )

        # Pick the best matching result based on media_type
        target = None
        for item in scraped:
            if item.media_type == media_type:
                target = item
                break
        if not target:
            target = scraped[0]

        if not target.url:
            return DownloadResult(
                success=False,
                error="Fallback scraper found no downloadable media.",
                media_type=media_type,
            )

        # Download the direct URL
        try:
            ext = "mp4" if target.media_type == "video" else "mp3"
            out_path = str(DOWNLOAD_DIR / f"{user_id}_fallback_{hash(url) & 0xFFFFFF:06x}.{ext}")

            resp = requests.get(
                target.url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=DOWNLOAD_TIMEOUT,
                stream=True,
            )
            resp.raise_for_status()

            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = os.path.getsize(out_path)
            if file_size > MAX_FILE_SIZE:
                os.remove(out_path)
                return DownloadResult(
                    success=False,
                    error=(
                        f"File is too large ({file_size / (1024*1024):.1f} MB). "
                        f"Telegram limit is {MAX_FILE_SIZE / (1024*1024):.0f} MB."
                    ),
                    media_type=media_type,
                )

            return DownloadResult(
                success=True,
                file_path=out_path,
                title=sanitize_filename(target.title),
                file_size=file_size,
                thumbnail=target.thumbnail,
                media_type=target.media_type,
            )

        except Exception as e:
            logger.error("Fallback download failed: %s", e)
            if os.path.exists(out_path):
                try:
                    os.remove(out_path)
                except OSError:
                    pass
            return DownloadResult(
                success=False,
                error=f"Fallback download failed: {str(e)[:200]}",
                media_type=media_type,
            )

    @staticmethod
    def cleanup_file(file_path: str | None) -> None:
        """Remove a downloaded file after sending."""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                logger.warning("Failed to cleanup file %s: %s", file_path, e)

    @staticmethod
    def cleanup_user_files(user_id: int) -> None:
        """Remove all downloaded files for a user."""
        if not DOWNLOAD_DIR.exists():
            return
        for f in DOWNLOAD_DIR.iterdir():
            if f.name.startswith(f"{user_id}_"):
                try:
                    f.unlink()
                except OSError:
                    pass


downloader = MediaDownloader()
