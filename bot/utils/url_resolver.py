"""URL shortener and redirect resolver.

Resolves shortened URLs (bit.ly, tinyurl, etc.) and intermediate redirects
to reach the original video source URL.
"""

import re
from urllib.parse import urlparse

import requests

from bot.utils.logger import logger

# Known URL shortener domains
_SHORTENER_DOMAINS = frozenset({
    "bit.ly", "tinyurl.com", "t.co", "goo.gl",
    "ow.ly", "is.gd", "buff.ly", "adf.ly",
    "tiny.cc", "lnkd.in", "db.tt", "qr.ae",
    "cur.lv", "ity.im", "q.gs", "po.st",
    "bc.vc", "soo.gd", "s2r.co", "clicky.me",
    "shorturl.at", "rb.gy", "cutt.ly", "t.ly",
    # Platform-specific shorteners
    "vm.tiktok.com", "vt.tiktok.com",
    "fb.watch", "pin.it", "redd.it",
    "dai.ly", "youtu.be", "instagr.am",
})

# Rotating user agents for resolver requests
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
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
]

_agent_index = 0


def _next_user_agent() -> str:
    """Rotate through user agents."""
    global _agent_index
    ua = _USER_AGENTS[_agent_index % len(_USER_AGENTS)]
    _agent_index += 1
    return ua


def is_shortened_url(url: str) -> bool:
    """Check if a URL is from a known URL shortener service."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    return domain in _SHORTENER_DOMAINS


def resolve_url(url: str, max_redirects: int = 10, timeout: int = 15) -> str:
    """Resolve a URL by following all redirects to the final destination.

    Works with bit.ly, tinyurl, t.co, and any other URL shortener
    by following HTTP redirects (301, 302, 303, 307, 308).

    Args:
        url: The URL to resolve
        max_redirects: Maximum number of redirects to follow
        timeout: Request timeout in seconds

    Returns:
        The final resolved URL, or the original URL on failure
    """
    if not is_shortened_url(url):
        return url

    logger.info("Resolving shortened URL: %s", url)

    try:
        session = requests.Session()
        session.max_redirects = max_redirects
        session.headers.update({
            "User-Agent": _next_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

        # Use HEAD request first (faster, no body download)
        response = session.head(
            url,
            allow_redirects=True,
            timeout=timeout,
        )

        final_url = response.url

        # Some shorteners don't respond to HEAD, fall back to GET
        if response.status_code >= 400:
            response = session.get(
                url,
                allow_redirects=True,
                timeout=timeout,
                stream=True,  # Don't download body
            )
            final_url = response.url
            response.close()

        if final_url != url:
            logger.info("Resolved %s -> %s", url, final_url)

        return final_url

    except requests.exceptions.TooManyRedirects:
        logger.warning("Too many redirects for %s", url)
        return url
    except requests.exceptions.Timeout:
        logger.warning("Timeout resolving %s", url)
        return url
    except requests.exceptions.RequestException as e:
        logger.warning("Error resolving URL %s: %s", url, e)
        return url


def resolve_url_sync(url: str) -> str:
    """Synchronous wrapper for resolve_url (for use in thread executors)."""
    return resolve_url(url)


def extract_video_id_from_url(url: str) -> str | None:
    """Try to extract a video/content ID from common URL patterns."""
    patterns = [
        # YouTube
        (r"(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)(?P<id>[\w-]{11})", "youtube"),
        # TikTok
        (r"tiktok\.com/@[\w.-]+/video/(?P<id>\d+)", "tiktok"),
        # Instagram
        (r"instagram\.com/(?:p|reel|tv)/(?P<id>[\w-]+)", "instagram"),
        # Facebook
        (r"facebook\.com/.*/videos/(?P<id>\d+)", "facebook"),
        # Twitter/X
        (r"(?:twitter|x)\.com/\w+/status/(?P<id>\d+)", "twitter"),
        # Vimeo
        (r"vimeo\.com/(?P<id>\d+)", "vimeo"),
        # Dailymotion
        (r"dailymotion\.com/video/(?P<id>[\w]+)", "dailymotion"),
    ]
    for pattern, _platform in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group("id")
    return None
