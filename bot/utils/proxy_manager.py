"""Proxy rotation and user-agent spoofing for rate limit bypass.

Provides rotating user agents and optional proxy support for
HTTP requests and yt-dlp downloads.
"""

import random
import time
from typing import Any

from bot.utils.logger import logger

# Comprehensive list of realistic user agents (updated regularly)
_USER_AGENTS = [
    # Chrome on Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    ),
    # Chrome on macOS
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    # Chrome on Linux
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    # Firefox on Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
        "Gecko/20100101 Firefox/128.0"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) "
        "Gecko/20100101 Firefox/127.0"
    ),
    # Firefox on macOS
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) "
        "Gecko/20100101 Firefox/128.0"
    ),
    # Firefox on Linux
    (
        "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
        "Gecko/20100101 Firefox/128.0"
    ),
    # Edge on Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
    ),
    # Safari on macOS
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.6 Safari/605.1.15"
    ),
]

# Proxy list (loaded from config or environment)
_proxies: list[str] = []
_proxy_index = 0
_proxy_failures: dict[str, int] = {}
_MAX_PROXY_FAILURES = 3


def get_random_user_agent() -> str:
    """Return a random user agent string."""
    return random.choice(_USER_AGENTS)


def get_rotating_user_agent() -> str:
    """Return user agents in a round-robin fashion."""
    index = int(time.time()) % len(_USER_AGENTS)
    return _USER_AGENTS[index]


def set_proxies(proxy_list: list[str]) -> None:
    """Set the proxy list for rotation.

    Proxies should be in format:
    - http://host:port
    - http://user:pass@host:port
    - socks5://host:port
    """
    global _proxies
    _proxies = [p.strip() for p in proxy_list if p.strip()]
    if _proxies:
        logger.info("Loaded %d proxies for rotation", len(_proxies))


def load_proxies_from_file(filepath: str) -> None:
    """Load proxies from a text file (one proxy per line)."""
    try:
        with open(filepath) as f:
            proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        set_proxies(proxies)
    except FileNotFoundError:
        logger.warning("Proxy file not found: %s", filepath)
    except Exception as e:
        logger.error("Error loading proxies from %s: %s", filepath, e)


def get_next_proxy() -> str | None:
    """Get the next proxy from the rotation list.

    Skips proxies that have failed too many times.
    Returns None if no proxies are available.
    """
    global _proxy_index

    if not _proxies:
        return None

    # Try each proxy, skip failed ones
    attempts = 0
    while attempts < len(_proxies):
        proxy = _proxies[_proxy_index % len(_proxies)]
        _proxy_index += 1
        attempts += 1

        failures = _proxy_failures.get(proxy, 0)
        if failures < _MAX_PROXY_FAILURES:
            return proxy

    # All proxies have failed too many times, reset and try again
    logger.warning("All proxies have exceeded failure threshold, resetting")
    _proxy_failures.clear()
    return _proxies[0] if _proxies else None


def report_proxy_failure(proxy: str) -> None:
    """Report that a proxy has failed."""
    _proxy_failures[proxy] = _proxy_failures.get(proxy, 0) + 1
    failures = _proxy_failures[proxy]
    logger.warning(
        "Proxy failure reported: %s (failures: %d/%d)",
        proxy,
        failures,
        _MAX_PROXY_FAILURES,
    )


def report_proxy_success(proxy: str) -> None:
    """Report that a proxy succeeded (reset failure count)."""
    if proxy in _proxy_failures:
        del _proxy_failures[proxy]


def get_yt_dlp_proxy_opts() -> dict[str, Any]:
    """Get yt-dlp options with proxy and user-agent rotation.

    Returns a dict that can be merged into yt-dlp options.
    """
    opts: dict[str, Any] = {
        "http_headers": {
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
        },
    }

    proxy = get_next_proxy()
    if proxy:
        opts["proxy"] = proxy
        logger.debug("Using proxy: %s", proxy)

    return opts


def get_requests_proxy_config() -> dict[str, str]:
    """Get proxy configuration for the requests library.

    Returns a dict suitable for requests.get(proxies=...).
    """
    proxy = get_next_proxy()
    if not proxy:
        return {}

    return {
        "http": proxy,
        "https": proxy,
    }


def get_proxy_stats() -> dict[str, Any]:
    """Return proxy pool statistics."""
    total = len(_proxies)
    failed = sum(1 for f in _proxy_failures.values() if f >= _MAX_PROXY_FAILURES)
    return {
        "total_proxies": total,
        "active_proxies": total - failed,
        "failed_proxies": failed,
        "has_proxies": total > 0,
    }
