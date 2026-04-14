"""Group-related handlers for the bot."""

from telegram import Update, ChatMemberUpdated
from telegram.constants import ChatMemberStatus, ChatType
from telegram.ext import ContextTypes

from bot.database.db import add_group, remove_group, upsert_user, is_user_banned
from bot.utils.helpers import extract_urls, detect_platform
from bot.utils.logger import logger


async def track_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Track when the bot is added to or removed from a group."""
    if not update.my_chat_member:
        return

    chat_member = update.my_chat_member
    chat = chat_member.chat

    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    new_status = chat_member.new_chat_member.status
    old_status = chat_member.old_chat_member.status

    added_by = chat_member.from_user.id if chat_member.from_user else 0

    # Bot was added to a group
    if (
        old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED)
        and new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR)
    ):
        add_group(chat.id, chat.title or "Unknown", added_by)
        logger.info("Bot added to group: %s (%s) by user %s", chat.title, chat.id, added_by)

        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    "\U0001f44b <b>Hello!</b>\n\n"
                    "I'm <b>Media Magic Bot</b> \U0001f3ac\n"
                    "Send me a video/media link and I'll download it for you!\n\n"
                    "Use /help for more info."
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Failed to send welcome message to group %s: %s", chat.id, e)

    # Bot was removed from a group
    elif (
        old_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR)
        and new_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED)
    ):
        remove_group(chat.id)
        logger.info("Bot removed from group: %s (%s)", chat.title, chat.id)


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle messages in groups - only respond to URLs or commands."""
    if not update.message or not update.message.text or not update.effective_user:
        return

    if not update.effective_chat:
        return

    # Only process in groups
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
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
        return

    # Check if message contains URLs
    urls = extract_urls(update.message.text)
    if not urls:
        return

    # Import here to avoid circular imports
    from bot.handlers.download import handle_url_message

    await handle_url_message(update, context)
