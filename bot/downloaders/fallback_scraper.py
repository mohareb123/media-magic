"""Fallback scraper using BeautifulSoup for when yt-dlp fails.

Attempts to extract direct video/audio URLs from page HTML by parsing
<video>, <source>, <meta>, and Open Graph tags.
"""

import re
from typing import NamedTuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from bot.utils.logger import logger

# Rotating user agents for scraping requests
_USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
        "Gecko/20100101 Firefox/128.0"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
    ),
]

_agent_index = 0


def _next_user_agent() -> str:
    """Rotate through user agents."""
    global _agent_index
    ua = _USER_AGENTS[_agent_index % len(_USER_AGENTS)]
    _agent_index += 1
    return ua


class ScrapedMedia(NamedTuple):
    """Result of scraping media from a page."""

    url: str | None
    title: str
    thumbnail: str | None
    media_type: str  # "video", "audio", "image"
    quality: str  # "unknown", "720p", "1080p", etc.


def scrape_media_urls(page_url: str, timeout: int = 20) -> list[ScrapedMedia]:
    """Scrape a page for direct media URLs using BeautifulSoup.

    This is the fallback mechanism when yt-dlp fails. It parses the HTML
    to find <video>, <source>, <audio>, and Open Graph meta tags.

    Args:
        page_url: The URL of the page to scrape
        timeout: Request timeout in seconds

    Returns:
        List of ScrapedMedia results with direct URLs
    """
    logger.info("Fallback scraper: attempting to scrape %s", page_url)

    try:
        headers = {
            "User-Agent": _next_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Referer": page_url,
        }

        response = requests.get(page_url, headers=headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results: list[ScrapedMedia] = []

        # Extract title
        title = _extract_title(soup)

        # Extract thumbnail from Open Graph
        thumbnail = _extract_og_image(soup, page_url)

        # 1. Check Open Graph video meta tags
        og_results = _extract_og_video(soup, page_url, title, thumbnail)
        results.extend(og_results)

        # 2. Check <video> tags and their <source> children
        video_results = _extract_video_tags(soup, page_url, title, thumbnail)
        results.extend(video_results)

        # 3. Check <audio> tags
        audio_results = _extract_audio_tags(soup, page_url, title, thumbnail)
        results.extend(audio_results)

        # 4. Check for JSON-LD structured data
        jsonld_results = _extract_json_ld(soup, page_url, title, thumbnail)
        results.extend(jsonld_results)

        # 5. Check for direct video URLs in scripts (common pattern)
        script_results = _extract_from_scripts(soup, page_url, title, thumbnail)
        results.extend(script_results)

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique: list[ScrapedMedia] = []
        for r in results:
            if r.url and r.url not in seen_urls:
                seen_urls.add(r.url)
                unique.append(r)

        logger.info(
            "Fallback scraper: found %d media URLs on %s", len(unique), page_url
        )
        return unique

    except requests.exceptions.RequestException as e:
        logger.warning("Fallback scraper failed for %s: %s", page_url, e)
        return []
    except Exception as e:
        logger.error("Fallback scraper error for %s: %s", page_url, e)
        return []


def _extract_title(soup: BeautifulSoup) -> str:
    """Extract page title from various sources."""
    # Try OG title first
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return str(og_title["content"])

    # Try Twitter title
    tw_title = soup.find("meta", attrs={"name": "twitter:title"})
    if tw_title and tw_title.get("content"):
        return str(tw_title["content"])

    # Fall back to <title> tag
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    return "Unknown"


def _extract_og_image(soup: BeautifulSoup, base_url: str) -> str | None:
    """Extract thumbnail from Open Graph meta tags."""
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return urljoin(base_url, str(og_image["content"]))
    return None


def _extract_og_video(
    soup: BeautifulSoup, base_url: str, title: str, thumbnail: str | None
) -> list[ScrapedMedia]:
    """Extract video URLs from Open Graph meta tags."""
    results: list[ScrapedMedia] = []

    for tag_name in ["og:video", "og:video:url", "og:video:secure_url"]:
        meta = soup.find("meta", property=tag_name)
        if meta and meta.get("content"):
            url = urljoin(base_url, str(meta["content"]))
            if _is_media_url(url):
                quality = _detect_quality_from_url(url)
                results.append(
                    ScrapedMedia(
                        url=url,
                        title=title,
                        thumbnail=thumbnail,
                        media_type="video",
                        quality=quality,
                    )
                )

    # Also check twitter:player:stream
    tw_stream = soup.find("meta", attrs={"name": "twitter:player:stream"})
    if tw_stream and tw_stream.get("content"):
        url = urljoin(base_url, str(tw_stream["content"]))
        if _is_media_url(url):
            results.append(
                ScrapedMedia(
                    url=url,
                    title=title,
                    thumbnail=thumbnail,
                    media_type="video",
                    quality=_detect_quality_from_url(url),
                )
            )

    return results


def _extract_video_tags(
    soup: BeautifulSoup, base_url: str, title: str, thumbnail: str | None
) -> list[ScrapedMedia]:
    """Extract URLs from <video> and <source> HTML tags."""
    results: list[ScrapedMedia] = []

    for video_tag in soup.find_all("video"):
        # Check src attribute on <video>
        src = video_tag.get("src")
        if src:
            url = urljoin(base_url, str(src))
            results.append(
                ScrapedMedia(
                    url=url,
                    title=title,
                    thumbnail=thumbnail,
                    media_type="video",
                    quality=_detect_quality_from_url(url),
                )
            )

        # Check <source> children
        for source in video_tag.find_all("source"):
            src = source.get("src")
            if src:
                url = urljoin(base_url, str(src))
                mime_type = source.get("type", "")
                if "audio" in str(mime_type):
                    media_type = "audio"
                else:
                    media_type = "video"
                results.append(
                    ScrapedMedia(
                        url=url,
                        title=title,
                        thumbnail=thumbnail,
                        media_type=media_type,
                        quality=_detect_quality_from_url(url),
                    )
                )

    return results


def _extract_audio_tags(
    soup: BeautifulSoup, base_url: str, title: str, thumbnail: str | None
) -> list[ScrapedMedia]:
    """Extract URLs from <audio> and <source> HTML tags."""
    results: list[ScrapedMedia] = []

    for audio_tag in soup.find_all("audio"):
        src = audio_tag.get("src")
        if src:
            url = urljoin(base_url, str(src))
            results.append(
                ScrapedMedia(
                    url=url,
                    title=title,
                    thumbnail=thumbnail,
                    media_type="audio",
                    quality="unknown",
                )
            )

        for source in audio_tag.find_all("source"):
            src = source.get("src")
            if src:
                url = urljoin(base_url, str(src))
                results.append(
                    ScrapedMedia(
                        url=url,
                        title=title,
                        thumbnail=thumbnail,
                        media_type="audio",
                        quality="unknown",
                    )
                )

    return results


def _extract_json_ld(
    soup: BeautifulSoup, base_url: str, title: str, thumbnail: str | None
) -> list[ScrapedMedia]:
    """Extract video URLs from JSON-LD structured data."""
    import json

    results: list[ScrapedMedia] = []

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                for item in data:
                    results.extend(_parse_jsonld_item(item, base_url, title, thumbnail))
            elif isinstance(data, dict):
                results.extend(_parse_jsonld_item(data, base_url, title, thumbnail))
        except (json.JSONDecodeError, TypeError):
            continue

    return results


def _parse_jsonld_item(
    data: dict, base_url: str, title: str, thumbnail: str | None
) -> list[ScrapedMedia]:
    """Parse a single JSON-LD item for video/audio URLs."""
    results: list[ScrapedMedia] = []
    schema_type = data.get("@type", "")

    if schema_type in ("VideoObject", "Movie", "TVEpisode"):
        content_url = data.get("contentUrl")
        if content_url:
            url = urljoin(base_url, str(content_url))
            ld_title = data.get("name", title)
            ld_thumb = data.get("thumbnailUrl", thumbnail)
            if isinstance(ld_thumb, list):
                ld_thumb = ld_thumb[0] if ld_thumb else thumbnail
            results.append(
                ScrapedMedia(
                    url=url,
                    title=str(ld_title),
                    thumbnail=str(ld_thumb) if ld_thumb else None,
                    media_type="video",
                    quality=_detect_quality_from_url(url),
                )
            )

    elif schema_type in ("AudioObject", "MusicRecording"):
        content_url = data.get("contentUrl")
        if content_url:
            url = urljoin(base_url, str(content_url))
            ld_title = data.get("name", title)
            results.append(
                ScrapedMedia(
                    url=url,
                    title=str(ld_title),
                    thumbnail=thumbnail,
                    media_type="audio",
                    quality="unknown",
                )
            )

    return results


def _extract_from_scripts(
    soup: BeautifulSoup, base_url: str, title: str, thumbnail: str | None
) -> list[ScrapedMedia]:
    """Extract direct media URLs from inline scripts (common pattern)."""
    results: list[ScrapedMedia] = []

    # Pattern: direct mp4/m4a/webm URLs in JavaScript
    media_url_pattern = re.compile(
        r'["\']'
        r'(https?://[^\s"\'<>]+\.(?:mp4|m4a|webm|mp3|ogg|m3u8)(?:\?[^\s"\'<>]*)?)'
        r'["\']',
        re.IGNORECASE,
    )

    for script in soup.find_all("script"):
        if not script.string:
            continue
        for match in media_url_pattern.finditer(script.string):
            url = match.group(1)
            ext = url.rsplit(".", 1)[-1].split("?")[0].lower()
            if ext in ("mp3", "m4a", "ogg"):
                media_type = "audio"
            else:
                media_type = "video"
            results.append(
                ScrapedMedia(
                    url=url,
                    title=title,
                    thumbnail=thumbnail,
                    media_type=media_type,
                    quality=_detect_quality_from_url(url),
                )
            )

    return results


def _is_media_url(url: str) -> bool:
    """Check if a URL likely points to a media file."""
    media_extensions = (".mp4", ".m4a", ".webm", ".mp3", ".ogg", ".m3u8", ".mpd")
    path = url.split("?")[0].lower()
    return any(path.endswith(ext) for ext in media_extensions)


def _detect_quality_from_url(url: str) -> str:
    """Try to detect video quality from URL patterns."""
    url_lower = url.lower()
    quality_patterns = [
        ("2160", "2160p"),
        ("1440", "1440p"),
        ("1080", "1080p"),
        ("720", "720p"),
        ("480", "480p"),
        ("360", "360p"),
        ("240", "240p"),
        ("hd", "hd"),
        ("sd", "sd"),
    ]
    for pattern, quality in quality_patterns:
        if pattern in url_lower:
            return quality
    return "unknown"
