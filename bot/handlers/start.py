"""Start and help command handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.config import OWNER_ID, SUPPORTED_PLATFORMS, BOT_LOGO
from bot.database.db import upsert_user, is_user_banned
from bot.utils.logger import logger


def _register_user(update: Update) -> None:
    """Register or update user in the database."""
    user = update.effective_user
    if user:
        upsert_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code,
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not update.effective_user or not update.message:
        return

    _register_user(update)

    if is_user_banned(update.effective_user.id):
        await update.message.reply_text(
            "\u26d4 You have been banned from using this bot.\n"
            "Contact the admin if you think this is a mistake."
        )
        return

    user_name = update.effective_user.first_name or "User"

    welcome_text = (
        f"\U0001f44b Welcome, <b>{user_name}</b>!\n\n"
        "\U0001f3ac <b>Media Magic Bot</b> - Your all-in-one media downloader!\n\n"
        "\U0001f4e5 <b>What I can do:</b>\n"
        "\u2022 Download videos in multiple qualities\n"
        "\u2022 Extract audio (MP3) from videos\n"
        "\u2022 Download thumbnails/images\n\n"
        "\U0001f310 <b>Supported Platforms:</b>\n"
        "\u2022 YouTube \u2022 TikTok \u2022 Instagram\n"
        "\u2022 Facebook \u2022 Twitter/X \u2022 Pinterest\n"
        "\u2022 Reddit \u2022 Vimeo \u2022 Dailymotion\n"
        "\u2022 SoundCloud \u2022 And more!\n\n"
        "\U0001f4a1 <b>How to use:</b>\n"
        "Just send me a link and I'll handle the rest!\n\n"
        "Use /help for more details."
    )

    keyboard = [
        [
            InlineKeyboardButton("\U0001f4d6 Help", callback_data="help"),
            InlineKeyboardButton("\U0001f310 Supported Sites", callback_data="platforms"),
        ],
        [
            InlineKeyboardButton("\U0001f4ca My Stats", callback_data="my_stats"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if BOT_LOGO.exists():
        try:
            with open(BOT_LOGO, "rb") as logo:
                await update.message.reply_photo(
                    photo=logo,
                    caption=welcome_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
        except Exception:
            await update.message.reply_text(
                welcome_text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
    else:
        await update.message.reply_text(
            welcome_text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    logger.info("User %s (%s) started the bot", update.effective_user.id, user_name)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not update.message:
        return

    _register_user(update)

    help_text = (
        "\U0001f4d6 <b>Media Magic Bot - Help Guide</b>\n\n"
        "\U0001f3ac <b>Download Video:</b>\n"
        "Send any video link to download it.\n"
        "Choose quality from the options shown.\n\n"
        "\U0001f3b5 <b>Download Audio (MP3):</b>\n"
        "Send a link, then choose 'Audio (MP3)' option.\n\n"
        "\U0001f5bc <b>Download Thumbnail:</b>\n"
        "Send a link, then choose 'Thumbnail' option.\n\n"
        "\U0001f4cb <b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/platforms - List supported platforms\n"
        "/mystats - View your download statistics\n"
        "/cancel - Cancel current operation\n\n"
        "\u26a0\ufe0f <b>Limits:</b>\n"
        "\u2022 Max file size: 50 MB (Telegram limit)\n"
        "\u2022 Max 50 downloads per day\n\n"
        "\U0001f6e0 <b>Support:</b>\n"
        "For issues or suggestions, contact the bot owner."
    )

    await update.message.reply_text(help_text, parse_mode="HTML")


async def platforms_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /platforms command."""
    if not update.message:
        return

    _register_user(update)

    platform_emojis = {
        "youtube": "\u25b6\ufe0f YouTube",
        "tiktok": "\U0001f3b5 TikTok",
        "instagram": "\U0001f4f7 Instagram",
        "facebook": "\U0001f4d8 Facebook",
        "twitter": "\U0001f426 Twitter/X",
        "pinterest": "\U0001f4cc Pinterest",
        "reddit": "\U0001f916 Reddit",
        "vimeo": "\U0001f3ac Vimeo",
        "dailymotion": "\U0001f4fa Dailymotion",
        "soundcloud": "\u2601\ufe0f SoundCloud",
    }

    platforms_text = "\U0001f310 <b>Supported Platforms:</b>\n\n"
    for key in SUPPORTED_PLATFORMS:
        name = platform_emojis.get(key, f"\U0001f517 {key.title()}")
        domains = ", ".join(SUPPORTED_PLATFORMS[key])
        platforms_text += f"{name}\n   <code>{domains}</code>\n\n"

    platforms_text += (
        "\U0001f4a1 <i>Just send a link from any of these platforms "
        "and I'll download the media for you!</i>"
    )

    await update.message.reply_text(platforms_text, parse_mode="HTML")


async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mystats command."""
    if not update.message or not update.effective_user:
        return

    _register_user(update)

    from bot.database.db import get_connection

    user_id = update.effective_user.id
    with get_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

        if not user:
            await update.message.reply_text("No stats available yet.")
            return

        total = user["total_downloads"]
        first_seen = user["first_seen"][:10]

        platform_rows = conn.execute(
            """
            SELECT platform, COUNT(*) as c FROM downloads
            WHERE user_id = ? AND status = 'completed' AND platform IS NOT NULL
            GROUP BY platform ORDER BY c DESC
            """,
            (user_id,),
        ).fetchall()

    stats_text = (
        "\U0001f4ca <b>Your Statistics</b>\n\n"
        f"\U0001f4e5 Total Downloads: <b>{total}</b>\n"
        f"\U0001f4c5 Member Since: <b>{first_seen}</b>\n"
    )

    if platform_rows:
        stats_text += "\n\U0001f310 <b>Downloads by Platform:</b>\n"
        for row in platform_rows:
            stats_text += f"   \u2022 {row['platform'].title()}: {row['c']}\n"

    await update.message.reply_text(stats_text, parse_mode="HTML")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command."""
    if not update.message:
        return
    context.user_data.clear()
    await update.message.reply_text(
        "\u274c Operation cancelled.", parse_mode="HTML"
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks for start menu."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    if query.data == "help":
        help_text = (
            "\U0001f4d6 <b>How to use Media Magic Bot:</b>\n\n"
            "1\ufe0f\u20e3 Send me a video/media link\n"
            "2\ufe0f\u20e3 Choose download type (Video/Audio/Thumbnail)\n"
            "3\ufe0f\u20e3 For videos, choose quality\n"
            "4\ufe0f\u20e3 Wait for the download to complete\n\n"
            "Use /help for the full help guide."
        )
        await query.edit_message_text(help_text, parse_mode="HTML")

    elif query.data == "platforms":
        await query.edit_message_text(
            "\U0001f310 <b>Supported Platforms:</b>\n\n"
            "\u25b6\ufe0f YouTube \u2022 \U0001f3b5 TikTok \u2022 \U0001f4f7 Instagram\n"
            "\U0001f4d8 Facebook \u2022 \U0001f426 Twitter/X \u2022 \U0001f4cc Pinterest\n"
            "\U0001f916 Reddit \u2022 \U0001f3ac Vimeo \u2022 \U0001f4fa Dailymotion\n"
            "\u2601\ufe0f SoundCloud\n\n"
            "Use /platforms for full details.",
            parse_mode="HTML",
        )

    elif query.data == "my_stats":
        if query.from_user:
            from bot.database.db import get_connection

            with get_connection() as conn:
                user = conn.execute(
                    "SELECT total_downloads FROM users WHERE user_id = ?",
                    (query.from_user.id,),
                ).fetchone()
            total = user["total_downloads"] if user else 0
            await query.edit_message_text(
                f"\U0001f4ca <b>Your Stats:</b>\n\n"
                f"\U0001f4e5 Total Downloads: <b>{total}</b>\n\n"
                f"Use /mystats for more details.",
                parse_mode="HTML",
            )
