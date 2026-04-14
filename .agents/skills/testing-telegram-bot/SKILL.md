# Testing Media Magic Telegram Bot

## Prerequisites

### Devin Secrets Needed
- `TELEGRAM_BOT_TOKEN` - The Telegram bot token (required to start the bot)
- `COOKIES_FILE` (optional) - Path to a cookies.txt file for YouTube authentication
- `POT_SERVER_URL` (optional) - URL for PO Token server for YouTube bot detection bypass

### System Dependencies
- Python 3.12+
- FFmpeg (required for audio/video conversion)
- pip packages from `bot/requirements.txt`

## Setup

```bash
# Install dependencies
pip install -r bot/requirements.txt

# Install FFmpeg if not present
sudo apt-get install -y ffmpeg
```

## Running the Bot

```bash
# Set the bot token
export TELEGRAM_BOT_TOKEN="your-token-here"

# Start the bot
python -m bot.main
```

Expected startup output:
- "Database initialized successfully"
- "Starting Media Magic Bot..."
- "Bot commands set successfully"

## Testing Approach

This bot is tested via shell-based Python assertions (no browser GUI needed). Key test areas:

### 1. Module Import Verification
```python
python3 -c "
from bot.config import BOT_LOGO, COOKIES_FILE, POT_SERVER_URL
from bot.downloaders.media_downloader import downloader
from bot.handlers.download import handle_url_message, download_callback
from bot.handlers.start import start_command
from bot.handlers.group import track_chat_member
from bot.handlers.admin import stats_command
print('All modules import successfully')
"
```

### 2. Platform Detection
```python
from bot.utils.helpers import detect_platform
assert detect_platform('https://youtube.com/watch?v=abc') == 'youtube'
assert detect_platform('https://box.com/file') is None  # Should NOT match twitter
```

### 3. Bot Startup Test
Run `timeout 8 python -m bot.main` with `TELEGRAM_BOT_TOKEN` set. Verify log output shows successful startup.

### 4. Database Verification
```python
from bot.database.db import init_db, get_connection
init_db()
with get_connection() as conn:
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    # Should include: users, downloads, groups, admin_logs
```

## Known Limitations

- **YouTube downloads on data center IPs**: YouTube blocks most data center IPs with "Sign in to confirm you're not a bot". This is an environment limitation, not a code bug. Workarounds:
  - Provide a `cookies.txt` file via `COOKIES_FILE` env var
  - Configure a PO Token server via `POT_SERVER_URL` env var
  - Run on a residential IP
- **Live Telegram flow testing**: Requires a Telegram account to test the full flow (send URL -> choose quality -> receive file). Bot startup and module tests can be done without an account.
- **Group join testing**: Requires adding the bot to a Telegram group, which needs a Telegram account.

## Bot Architecture

- `bot/main.py` - Entry point, registers handlers
- `bot/handlers/start.py` - /start, /help, /platforms commands
- `bot/handlers/download.py` - URL detection, quality selection, download flow
- `bot/handlers/group.py` - Group join/leave tracking
- `bot/handlers/admin.py` - /ban, /unban, /stats, /broadcast (owner only)
- `bot/downloaders/media_downloader.py` - yt-dlp wrapper for all platforms
- `bot/database/db.py` - SQLite database operations
- `bot/config.py` - All configuration constants
- `bot/assets/bot_logo.jpg` - Bot branding image
