"""Download handlers for processing media URLs."""

import asyncio
import hashlib
import html
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.config import MAX_DOWNLOADS_PER_DAY, OWNER_ID, BOT_LOGO
from bot.database.db import (
    is_user_banned,
    record_download,
    update_download_status,
    upsert_user,
    get_user_download_count_today,
)
from bot.downloaders.download_queue import DownloadTask, download_queue
from bot.downloaders.media_downloader import downloader
from bot.utils.helpers import extract_urls, detect_platform, validate_and_detect, format_file_size
from bot.utils.logger import logger
from bot.utils.url_resolver import resolve_url, is_shortened_url

# In-memory URL store keyed by short hash to avoid callback_data size limits.
# Each entry includes a timestamp for TTL-based eviction.
_pending_urls: dict[str, dict[str, str | None | float]] = {}
_PENDING_URL_TTL = 1800  # 30 minutes
_PENDING_URL_MAX = 500  # hard cap on entries


def _evict_expired_urls() -> None:
    """Remove entries older than _PENDING_URL_TTL."""
    now = time.monotonic()
    expired = [k for k, v in _pending_urls.items() if now - (v.get("_ts") or 0) > _PENDING_URL_TTL]
    for k in expired:
        _pending_urls.pop(k, None)


def _store_url(url: str, platform: str | None, user_id: int) -> str:
    """Store a URL and return a short key for callback_data."""
    _evict_expired_urls()
    # If still over the cap, drop the oldest entries
    if len(_pending_urls) >= _PENDING_URL_MAX:
        sorted_keys = sorted(_pending_urls, key=lambda k: _pending_urls[k].get("_ts") or 0)
        for k in sorted_keys[: len(_pending_urls) - _PENDING_URL_MAX + 1]:
            _pending_urls.pop(k, None)
    key = hashlib.md5(f"{user_id}:{url}".encode()).hexdigest()[:8]
    _pending_urls[key] = {"url": url, "platform": platform, "_ts": time.monotonic()}
    return key


def _get_url(key: str) -> tuple[str | None, str | None]:
    """Retrieve a stored URL by key."""
    entry = _pending_urls.get(key)
    if entry:
        return entry["url"], entry["platform"]
    return None, None


def _remove_url(key: str) -> None:
    """Remove a stored URL entry."""
    _pending_urls.pop(key, None)


async def handle_url_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages that contain URLs."""
    if not update.message or not update.message.text or not update.effective_user:
        return

    user = update.effective_user
    upsert_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
    )

    if is_user_banned(user.id):
        await update.message.reply_text(
            "\u26d4 You have been banned from using this bot."
        )
        return

    urls = extract_urls(update.message.text)
    if not urls:
        return

    # Rate limiting (skip for owner)
    if user.id != OWNER_ID:
        today_count = get_user_download_count_today(user.id)
        if today_count >= MAX_DOWNLOADS_PER_DAY:
            await update.message.reply_text(
                f"\u26a0\ufe0f You've reached the daily download limit "
                f"({MAX_DOWNLOADS_PER_DAY} downloads). Try again tomorrow!"
            )
            return

    url = urls[0]  # Process the first URL

    # Resolve shortened URLs (bit.ly, tinyurl, etc.) in executor to avoid blocking
    if is_shortened_url(url):
        logger.info("Resolving shortened URL: %s", url)
        url = await asyncio.get_event_loop().run_in_executor(None, resolve_url, url)

    # Enhanced platform detection with regex validation
    validation = validate_and_detect(url)
    platform = validation.platform or detect_platform(url)

    # Store URL with a unique key tied to this specific link
    url_key = _store_url(url, platform, user.id)

    platform_name = platform.title() if platform else "Unknown"
    # Add content type info if available
    if validation.url_type and validation.url_type not in ("video", "audio"):
        platform_name += f" ({validation.url_type.title()})"

    keyboard = [
        [
            InlineKeyboardButton(
                "\U0001f3ac Video (Best)", callback_data=f"dl_{url_key}_video_best"
            ),
            InlineKeyboardButton(
                "\U0001f3b5 Audio (MP3)", callback_data=f"dl_{url_key}_audio"
            ),
        ],
        [
            InlineKeyboardButton(
                "\U0001f4f9 1080p", callback_data=f"dl_{url_key}_video_1080p"
            ),
            InlineKeyboardButton(
                "\U0001f4f9 720p", callback_data=f"dl_{url_key}_video_720p"
            ),
            InlineKeyboardButton(
                "\U0001f4f9 480p", callback_data=f"dl_{url_key}_video_480p"
            ),
        ],
        [
            InlineKeyboardButton(
                "\U0001f4f9 360p", callback_data=f"dl_{url_key}_video_360p"
            ),
            InlineKeyboardButton(
                "\U0001f5bc Thumbnail", callback_data=f"dl_{url_key}_thumbnail"
            ),
        ],
        [
            InlineKeyboardButton("\u274c Cancel", callback_data=f"dl_{url_key}_cancel"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"\U0001f517 <b>Link detected!</b>\n"
        f"\U0001f310 Platform: <b>{platform_name}</b>\n\n"
        f"Choose what you want to download:",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )

    logger.info(
        "User %s (%s) sent URL: %s [platform: %s]",
        user.id,
        user.username,
        url,
        platform_name,
    )


async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle download option callbacks."""
    query = update.callback_query
    if not query or not query.data or not query.from_user:
        return

    await query.answer()

    # Parse callback data: dl_{url_key}_{action}
    parts = query.data.split("_", 2)  # ["dl", url_key, action_rest]
    if len(parts) < 3:
        return

    url_key = parts[1]
    action = parts[2]

    if action == "cancel":
        _remove_url(url_key)
        await query.edit_message_text("\u274c Download cancelled.")
        return

    url, platform = _get_url(url_key)

    if not url:
        await query.edit_message_text(
            "\u26a0\ufe0f Session expired. Please send the link again."
        )
        return

    user_id = query.from_user.id

    # Determine download type and quality
    if action == "audio":
        media_type = "audio"
        quality = "best"
        status_text = "\U0001f3b5 Downloading audio..."
    elif action == "thumbnail":
        media_type = "photo"
        quality = "best"
        status_text = "\U0001f5bc Downloading thumbnail..."
    else:
        media_type = "video"
        quality = action.replace("video_", "")
        quality_label = quality.upper() if quality != "best" else "Best Quality"
        status_text = f"\U0001f3ac Downloading video ({quality_label})..."

    # Show queue position if downloads are active
    active = download_queue.get_active_count()
    queue_info = ""
    if active >= 2:
        queue_info = f"\n\U0001f4cb Queue position: {active + 1}"

    # Update message to show progress
    await query.edit_message_text(
        f"{status_text}\n\n"
        f"\u23f3 Please wait, this may take a moment...{queue_info}",
        parse_mode="HTML",
    )

    # Record the download in database
    download_id = record_download(
        user_id=user_id,
        url=url,
        platform=platform,
        media_type=media_type,
        quality=quality,
    )

    result_file_path: str | None = None

    try:
        # Build the download coroutine
        async def _do_download():
            if media_type == "audio":
                return await downloader.download_audio(url, user_id=user_id)
            elif media_type == "photo":
                return await downloader.download_thumbnail(url, user_id=user_id)
            else:
                return await downloader.download_video(url, quality=quality, user_id=user_id)

        # Execute via the download queue (concurrency-controlled)
        task = DownloadTask(
            task_id=f"{user_id}_{url_key}",
            user_id=user_id,
            url=url,
            download_fn=_do_download,
        )
        result = await download_queue.submit(task)

        if result.success and result.file_path:
            result_file_path = result.file_path

        if not result.success:
            update_download_status(download_id, "failed", error_message=result.error)
            safe_error = html.escape(result.error or "Unknown error")
            await query.edit_message_text(
                f"\u274c <b>Download Failed</b>\n\n"
                f"Error: {safe_error}",
                parse_mode="HTML",
            )
            logger.warning(
                "Download failed for user %s, URL: %s, Error: %s",
                user_id,
                url,
                result.error,
            )
            return

        # Send the file
        file_size_text = format_file_size(result.file_size)
        safe_title = html.escape(result.title)
        caption = (
            f"\U0001f4e5 <b>{safe_title}</b>\n"
            f"\U0001f4c1 Size: {file_size_text}"
        )
        if result.duration and media_type != "photo":
            minutes, seconds = divmod(result.duration, 60)
            caption += f"\n\u23f1 Duration: {minutes}:{seconds:02d}"

        caption += "\n\n\U0001f916 <b>Media Magic Bot</b> | @Nsr7Memobot"

        if result.file_path:
            with open(result.file_path, "rb") as f:
                if media_type == "audio":
                    await query.message.reply_audio(
                        audio=f,
                        caption=caption,
                        parse_mode="HTML",
                        title=result.title,
                    )
                elif media_type == "photo":
                    await query.message.reply_photo(
                        photo=f,
                        caption=caption,
                        parse_mode="HTML",
                    )
                else:
                    await query.message.reply_video(
                        video=f,
                        caption=caption,
                        parse_mode="HTML",
                        supports_streaming=True,
                    )

        # Send bot logo after successful download
        if BOT_LOGO.exists():
            try:
                with open(BOT_LOGO, "rb") as logo:
                    await query.message.reply_photo(
                        photo=logo,
                        caption=(
                            "\u2705 <b>Download completed successfully!</b>\n"
                            "\U0001f916 <b>Media Magic Bot</b> | @Nsr7Memobot\n"
                            "\U0001f4e5 Send another link to download more!"
                        ),
                        parse_mode="HTML",
                    )
            except Exception as e:
                logger.warning("Failed to send bot logo: %s", e)

        # Update status
        update_download_status(download_id, "completed", file_size=result.file_size)

        # Delete the progress message
        try:
            await query.message.delete()
        except Exception:
            pass

        # Cleanup downloaded file
        downloader.cleanup_file(result.file_path)

        logger.info(
            "Download completed for user %s: %s [%s, %s, %s]",
            user_id,
            url,
            media_type,
            quality,
            file_size_text,
        )

    except Exception as e:
        update_download_status(download_id, "failed", error_message=str(e))
        try:
            await query.edit_message_text(
                "\u274c <b>Download Failed</b>\n\n"
                "An unexpected error occurred. Please try again later.",
                parse_mode="HTML",
            )
        except Exception:
            pass
        logger.error(
            "Unexpected error downloading for user %s: %s", user_id, e, exc_info=True
        )
        # Cleanup file on error
        if result_file_path:
            downloader.cleanup_file(result_file_path)
    finally:
        _remove_url(url_key)
