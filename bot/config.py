"""Bot configuration and environment variables."""

import os
from pathlib import Path

# Bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Owner / Developer ID
OWNER_ID = 6570434162

# Database path
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "bot.db"

# Bot assets
ASSETS_DIR = BASE_DIR / "assets"
BOT_LOGO = ASSETS_DIR / "bot_logo.jpg"

# Cookies file for YouTube authentication (optional)
COOKIES_FILE = os.getenv("COOKIES_FILE", "")

# Download settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB (Telegram limit)
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_TIMEOUT = 300  # 5 minutes

# Supported platforms
SUPPORTED_PLATFORMS = {
    "youtube": ["youtube.com", "youtu.be", "youtube.com/shorts"],
    "tiktok": ["tiktok.com", "vm.tiktok.com"],
    "instagram": ["instagram.com", "instagr.am"],
    "facebook": ["facebook.com", "fb.watch", "fb.com", "m.facebook.com"],
    "twitter": ["twitter.com", "x.com"],
    "pinterest": ["pinterest.com", "pin.it"],
    "reddit": ["reddit.com", "redd.it"],
    "vimeo": ["vimeo.com"],
    "dailymotion": ["dailymotion.com", "dai.ly"],
    "soundcloud": ["soundcloud.com"],
}

# Video quality options
VIDEO_QUALITIES = {
    "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]",
    "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
    "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]",
    "360p": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]",
}

# Audio format
AUDIO_FORMAT = "mp3"
AUDIO_QUALITY = "192"

# Rate limiting
MAX_DOWNLOADS_PER_DAY = 50

# Logging
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "bot.log"

# PO Token server URL for YouTube (optional)
POT_SERVER_URL = os.getenv("POT_SERVER_URL", "")

# Browser automation for YouTube cookie extraction (optional)
BROWSER_COOKIES_ENABLED = os.getenv("BROWSER_COOKIES_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)
BROWSER_COOKIES_PATH = BASE_DIR / "data" / "youtube_cookies.txt"
