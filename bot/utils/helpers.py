"""Helper utilities for the bot."""

import re
from urllib.parse import urlparse

from bot.config import SUPPORTED_PLATFORMS


def extract_urls(text: str) -> list[str]:
    """Extract URLs from a text message."""
    url_pattern = re.compile(
        r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
        r"(?:/[^\s]*)?"
    )
    return url_pattern.findall(text)


def detect_platform(url: str) -> str | None:
    """Detect which platform a URL belongs to."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")

    for platform, domains in SUPPORTED_PLATFORMS.items():
        for d in domains:
            if d in domain:
                return platform
    return None


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def sanitize_filename(filename: str) -> str:
    """Remove or replace characters that are not safe for filenames."""
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    filename = filename.strip(". ")
    if len(filename) > 200:
        filename = filename[:200]
    return filename or "download"


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special_chars = r"_*[]()~`>#+-=|{}.!"
    escaped = ""
    for char in text:
        if char in special_chars:
            escaped += f"\\{char}"
        else:
            escaped += char
    return escaped
