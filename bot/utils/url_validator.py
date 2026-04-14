"""Advanced URL validation with platform-specific regex patterns."""

import re
from typing import NamedTuple


class URLValidationResult(NamedTuple):
    """Result of URL validation."""

    is_valid: bool
    platform: str | None
    url_type: str | None  # "video", "shorts", "reel", "story", "audio", etc.
    content_id: str | None  # Extracted video/content ID when possible


# Platform-specific regex patterns
_PLATFORM_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "youtube": [
        # Standard watch URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)"
            r"/watch\?(?:.*&)?v=(?P<id>[\w-]{11})",
            re.IGNORECASE,
        ),
        # Short URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?youtu\.be/(?P<id>[\w-]{11})",
            re.IGNORECASE,
        ),
        # Shorts
        re.compile(
            r"(?:https?://)?(?:www\.)?youtube\.com/shorts/(?P<id>[\w-]{11})",
            re.IGNORECASE,
        ),
        # Embed URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?youtube\.com/embed/(?P<id>[\w-]{11})",
            re.IGNORECASE,
        ),
        # Music URLs
        re.compile(
            r"(?:https?://)?music\.youtube\.com/watch\?(?:.*&)?v=(?P<id>[\w-]{11})",
            re.IGNORECASE,
        ),
        # Live URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?youtube\.com/live/(?P<id>[\w-]{11})",
            re.IGNORECASE,
        ),
    ],
    "tiktok": [
        # Standard video URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?tiktok\.com/@[\w.-]+/video/(?P<id>\d+)",
            re.IGNORECASE,
        ),
        # Short/share URLs
        re.compile(
            r"(?:https?://)?(?:vm|vt)\.tiktok\.com/(?P<id>[\w-]+)",
            re.IGNORECASE,
        ),
        # Mobile URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?tiktok\.com/t/(?P<id>[\w-]+)",
            re.IGNORECASE,
        ),
    ],
    "instagram": [
        # Posts
        re.compile(
            r"(?:https?://)?(?:www\.)?instagram\.com/p/(?P<id>[\w-]+)",
            re.IGNORECASE,
        ),
        # Reels
        re.compile(
            r"(?:https?://)?(?:www\.)?instagram\.com/reel/(?P<id>[\w-]+)",
            re.IGNORECASE,
        ),
        # Stories
        re.compile(
            r"(?:https?://)?(?:www\.)?instagram\.com/stories/[\w.-]+/(?P<id>\d+)",
            re.IGNORECASE,
        ),
        # TV/IGTV
        re.compile(
            r"(?:https?://)?(?:www\.)?instagram\.com/tv/(?P<id>[\w-]+)",
            re.IGNORECASE,
        ),
        # Short URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?instagr\.am/p/(?P<id>[\w-]+)",
            re.IGNORECASE,
        ),
    ],
    "facebook": [
        # Video URLs
        re.compile(
            r"(?:https?://)?(?:www\.|m\.)?facebook\.com/.+/videos/(?P<id>\d+)",
            re.IGNORECASE,
        ),
        # Watch URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?facebook\.com/watch/?\?v=(?P<id>\d+)",
            re.IGNORECASE,
        ),
        # Reel URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?facebook\.com/reel/(?P<id>\d+)",
            re.IGNORECASE,
        ),
        # fb.watch short URLs
        re.compile(
            r"(?:https?://)?fb\.watch/(?P<id>[\w-]+)",
            re.IGNORECASE,
        ),
        # fb.com short URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?fb\.com/(?P<id>[\w/]+)",
            re.IGNORECASE,
        ),
        # Story URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?facebook\.com/stories/(?P<id>[\w/]+)",
            re.IGNORECASE,
        ),
    ],
    "twitter": [
        # Standard tweet URLs (twitter.com and x.com)
        re.compile(
            r"(?:https?://)?(?:www\.)?(?:twitter|x)\.com/\w+/status/(?P<id>\d+)",
            re.IGNORECASE,
        ),
        # Mobile URLs
        re.compile(
            r"(?:https?://)?mobile\.(?:twitter|x)\.com/\w+/status/(?P<id>\d+)",
            re.IGNORECASE,
        ),
        # t.co short URLs
        re.compile(
            r"(?:https?://)?t\.co/(?P<id>[\w]+)",
            re.IGNORECASE,
        ),
    ],
    "pinterest": [
        # Pin URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?pinterest\.com/pin/(?P<id>\d+)",
            re.IGNORECASE,
        ),
        # Short URLs
        re.compile(
            r"(?:https?://)?pin\.it/(?P<id>[\w]+)",
            re.IGNORECASE,
        ),
    ],
    "reddit": [
        # Post URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?reddit\.com/r/\w+/comments/(?P<id>\w+)",
            re.IGNORECASE,
        ),
        # Short URLs
        re.compile(
            r"(?:https?://)?redd\.it/(?P<id>\w+)",
            re.IGNORECASE,
        ),
    ],
    "vimeo": [
        # Standard URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?vimeo\.com/(?P<id>\d+)",
            re.IGNORECASE,
        ),
        # Player embed URLs
        re.compile(
            r"(?:https?://)?player\.vimeo\.com/video/(?P<id>\d+)",
            re.IGNORECASE,
        ),
    ],
    "dailymotion": [
        # Standard URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?dailymotion\.com/video/(?P<id>[\w]+)",
            re.IGNORECASE,
        ),
        # Short URLs
        re.compile(
            r"(?:https?://)?dai\.ly/(?P<id>[\w]+)",
            re.IGNORECASE,
        ),
    ],
    "soundcloud": [
        # Track URLs
        re.compile(
            r"(?:https?://)?(?:www\.)?soundcloud\.com/(?P<id>[\w-]+/[\w-]+)",
            re.IGNORECASE,
        ),
    ],
}

# URL type detection based on path patterns
_URL_TYPE_HINTS: dict[str, str] = {
    "/shorts/": "shorts",
    "/reel/": "reel",
    "/reels/": "reel",
    "/stories/": "story",
    "/tv/": "igtv",
    "/live/": "live",
    "soundcloud.com": "audio",
}


def validate_url(url: str) -> URLValidationResult:
    """Validate a URL against platform-specific patterns.

    Returns a URLValidationResult with platform, type, and content ID.
    """
    for platform, patterns in _PLATFORM_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(url)
            if match:
                content_id = match.group("id") if "id" in match.groupdict() else None
                url_type = _detect_url_type(url, platform)
                return URLValidationResult(
                    is_valid=True,
                    platform=platform,
                    url_type=url_type,
                    content_id=content_id,
                )

    # Check for generic URL (not a known platform but still a valid URL)
    generic = re.match(r"https?://[^\s]+", url, re.IGNORECASE)
    if generic:
        return URLValidationResult(
            is_valid=True,
            platform=None,
            url_type=None,
            content_id=None,
        )

    return URLValidationResult(
        is_valid=False,
        platform=None,
        url_type=None,
        content_id=None,
    )


def _detect_url_type(url: str, platform: str) -> str:
    """Detect the type of content from the URL path."""
    url_lower = url.lower()
    for hint_key, hint_type in _URL_TYPE_HINTS.items():
        if hint_key in url_lower:
            return hint_type
    if platform == "soundcloud":
        return "audio"
    return "video"


def is_shortened_url(url: str) -> bool:
    """Check if a URL is from a known URL shortener service."""
    shortener_domains = [
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
    ]
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    return domain in shortener_domains
