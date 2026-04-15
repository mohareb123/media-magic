# Media Magic Telegram Bot

A fully-featured Telegram bot for downloading videos, audio, and images from popular platforms.

## Supported Platforms

- YouTube
- TikTok
- Instagram
- Facebook
- Twitter/X
- Pinterest
- Reddit
- Vimeo
- Dailymotion
- SoundCloud

## Features

- Download videos in multiple qualities (Best, 1080p, 720p, 480p, 360p)
- Extract audio as MP3 from any video
- Download thumbnails/images
- Works in private chats and groups
- Admin panel with user management
- Usage statistics and logging
- Rate limiting (50 downloads/day per user)
- Automatic error handling and recovery

## Requirements

- Python 3.11+
- FFmpeg installed on the system

## Quick Start

1. **Install FFmpeg:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ffmpeg

   # macOS
   brew install ffmpeg
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set the bot token:**
   ```bash
   export TELEGRAM_BOT_TOKEN="your-bot-token-here"
   ```
   Or create a `.env` file in the `bot/` directory:
   ```
   TELEGRAM_BOT_TOKEN=your-bot-token-here
   ```

4. **Run the bot:**
   ```bash
   # From the project root directory:
   python -m bot.main

   # Or using the runner script (loads .env automatically):
   python bot/run.py
   ```

## Docker

```bash
docker build -t media-magic-bot ./bot
docker run -e TELEGRAM_BOT_TOKEN="your-token" media-magic-bot
```

## User Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help guide |
| `/platforms` | List supported platforms |
| `/mystats` | View your download statistics |
| `/cancel` | Cancel current operation |

## Admin Commands

| Command | Description |
|---------|-------------|
| `/admin` | Show admin commands |
| `/stats` | View bot statistics |
| `/ban <user_id> [reason]` | Ban a user |
| `/unban <user_id>` | Unban a user |
| `/broadcast <message>` | Send message to all users |
| `/recent` | View recent downloads |

## Admin ID

The bot owner/developer ID is configured in `config.py`:
```python
OWNER_ID = 6570434162
```

## Architecture

```
bot/
├── main.py                  # Entry point
├── run.py                   # Runner with .env loading
├── config.py                # Configuration
├── handlers/
│   ├── start.py             # Start/help commands
│   ├── download.py          # Download handlers
│   ├── admin.py             # Admin commands
│   └── group.py             # Group handlers
├── downloaders/
│   └── media_downloader.py  # yt-dlp based downloader
├── database/
│   └── db.py                # SQLite database
├── utils/
│   ├── logger.py            # Logging setup
│   └── helpers.py           # Helper functions
├── requirements.txt
├── Dockerfile
└── .env.example
```
