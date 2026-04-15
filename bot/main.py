"""Main entry point for the Media Magic Telegram Bot."""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import the bot package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters,
)

from bot.config import BOT_TOKEN, DOWNLOAD_DIR
from bot.database.db import init_db
from bot.handlers.start import (
    start_command,
    help_command,
    platforms_command,
    my_stats_command,
    cancel_command,
    button_callback,
)
from bot.handlers.download import handle_url_message, download_callback
from bot.handlers.admin import (
    stats_command,
    ban_command,
    unban_command,
    broadcast_command,
    recent_command,
    admin_help_command,
)
from bot.handlers.group import track_chat_member, handle_group_message
from bot.utils.logger import logger


async def error_handler(update: object, context: object) -> None:
    """Global error handler for the bot."""
    from telegram.ext import ContextTypes

    ctx = context  # type: ignore[assignment]
    logger.error("Exception while handling an update:", exc_info=ctx.error)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "\u26a0\ufe0f An error occurred while processing your request.\n"
                "Please try again later."
            )
        except Exception:
            pass


async def post_init(application: Application) -> None:
    """Set bot commands after initialization."""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help guide"),
        BotCommand("platforms", "List supported platforms"),
        BotCommand("mystats", "View your download statistics"),
        BotCommand("cancel", "Cancel current operation"),
        BotCommand("admin", "Admin commands (admin only)"),
        BotCommand("stats", "Bot statistics (admin only)"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set successfully")


def main() -> None:
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        print(
            "ERROR: TELEGRAM_BOT_TOKEN environment variable is not set.\n"
            "Please set it before running the bot:\n"
            "  export TELEGRAM_BOT_TOKEN='your-bot-token-here'\n"
            "Or create a .env file with:\n"
            "  TELEGRAM_BOT_TOKEN=your-bot-token-here"
        )
        sys.exit(1)

    # Initialize database
    init_db()

    # Create downloads directory
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Build the application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # --- Register Handlers ---

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("platforms", platforms_command))
    application.add_handler(CommandHandler("mystats", my_stats_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    # Admin command handlers
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("recent", recent_command))
    application.add_handler(CommandHandler("admin", admin_help_command))

    # Callback query handlers
    application.add_handler(
        CallbackQueryHandler(download_callback, pattern=r"^dl_")
    )
    application.add_handler(
        CallbackQueryHandler(button_callback, pattern=r"^(help|platforms|my_stats)$")
    )

    # Chat member handler (for group tracking)
    application.add_handler(
        ChatMemberHandler(track_chat_member, ChatMemberHandler.MY_CHAT_MEMBER)
    )

    # Message handlers
    # Handle URLs in private chats
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Entity("url") & filters.ChatType.PRIVATE,
            handle_url_message,
        )
    )
    # Also catch text that might contain URLs (without entity detection)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            handle_url_message,
        )
    )
    # Handle URLs in groups
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            handle_group_message,
        )
    )

    # Error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("Starting Media Magic Bot...")
    print("\U0001f680 Media Magic Bot is running! Press Ctrl+C to stop.")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
