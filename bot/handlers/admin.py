"""Admin command handlers for bot management."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import OWNER_ID
from bot.database.db import (
    ban_user,
    unban_user,
    get_stats,
    get_recent_downloads,
    get_all_user_ids,
    log_admin_action,
)
from bot.utils.logger import logger


def is_admin(user_id: int) -> bool:
    """Check if a user is the bot admin/owner."""
    return user_id == OWNER_ID


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command (admin only)."""
    if not update.message or not update.effective_user:
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("\u26d4 This command is for admins only.")
        return

    stats = get_stats()

    platform_text = ""
    if stats["platform_stats"]:
        platform_text = "\n\U0001f310 <b>Downloads by Platform:</b>\n"
        for platform, count in stats["platform_stats"].items():
            platform_text += f"   \u2022 {platform.title()}: {count}\n"

    stats_text = (
        "\U0001f4ca <b>Bot Statistics</b>\n\n"
        f"\U0001f465 Total Users: <b>{stats['total_users']}</b>\n"
        f"\U0001f4c8 Active Users (7d): <b>{stats['active_users_7d']}</b>\n"
        f"\U0001f4e5 Total Downloads: <b>{stats['total_downloads']}</b>\n"
        f"\U0001f4c5 Downloads Today: <b>{stats['downloads_today']}</b>\n"
        f"\U0001f6ab Banned Users: <b>{stats['banned_users']}</b>\n"
        f"\U0001f465 Active Groups: <b>{stats['total_groups']}</b>\n"
        f"{platform_text}"
    )

    await update.message.reply_text(stats_text, parse_mode="HTML")
    logger.info("Admin %s requested stats", update.effective_user.id)


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ban <user_id> [reason] command (admin only)."""
    if not update.message or not update.effective_user:
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("\u26d4 This command is for admins only.")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "\u26a0\ufe0f Usage: /ban <user_id> [reason]\n"
            "Example: /ban 123456789 Spam"
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("\u26a0\ufe0f Invalid user ID.")
        return

    if target_user_id == OWNER_ID:
        await update.message.reply_text("\u26a0\ufe0f Cannot ban the bot owner.")
        return

    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"

    if ban_user(target_user_id, reason):
        log_admin_action(
            admin_id=update.effective_user.id,
            action="ban",
            target_user_id=target_user_id,
            details=reason,
        )
        await update.message.reply_text(
            f"\u2705 User <code>{target_user_id}</code> has been banned.\n"
            f"Reason: {reason}",
            parse_mode="HTML",
        )
        logger.info(
            "Admin %s banned user %s: %s",
            update.effective_user.id,
            target_user_id,
            reason,
        )
    else:
        await update.message.reply_text(
            f"\u26a0\ufe0f User <code>{target_user_id}</code> not found in database.\n"
            "The user needs to start the bot first.",
            parse_mode="HTML",
        )


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unban <user_id> command (admin only)."""
    if not update.message or not update.effective_user:
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("\u26d4 This command is for admins only.")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "\u26a0\ufe0f Usage: /unban <user_id>\n"
            "Example: /unban 123456789"
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("\u26a0\ufe0f Invalid user ID.")
        return

    if unban_user(target_user_id):
        log_admin_action(
            admin_id=update.effective_user.id,
            action="unban",
            target_user_id=target_user_id,
        )
        await update.message.reply_text(
            f"\u2705 User <code>{target_user_id}</code> has been unbanned.",
            parse_mode="HTML",
        )
        logger.info("Admin %s unbanned user %s", update.effective_user.id, target_user_id)
    else:
        await update.message.reply_text(
            f"\u26a0\ufe0f User <code>{target_user_id}</code> not found in database.",
            parse_mode="HTML",
        )


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /broadcast <message> command (admin only)."""
    if not update.message or not update.effective_user:
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("\u26d4 This command is for admins only.")
        return

    if not context.args:
        await update.message.reply_text(
            "\u26a0\ufe0f Usage: /broadcast <message>\n"
            "Example: /broadcast Bot maintenance in 1 hour!"
        )
        return

    broadcast_text = " ".join(context.args)
    user_ids = get_all_user_ids()

    sent = 0
    failed = 0

    status_msg = await update.message.reply_text(
        f"\U0001f4e2 Broadcasting to {len(user_ids)} users..."
    )

    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"\U0001f4e2 <b>Announcement</b>\n\n{broadcast_text}",
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1

    log_admin_action(
        admin_id=update.effective_user.id,
        action="broadcast",
        details=f"Sent: {sent}, Failed: {failed}, Message: {broadcast_text[:100]}",
    )

    await status_msg.edit_text(
        f"\U0001f4e2 <b>Broadcast Complete</b>\n\n"
        f"\u2705 Sent: {sent}\n"
        f"\u274c Failed: {failed}\n"
        f"\U0001f4ac Message: {broadcast_text[:100]}",
        parse_mode="HTML",
    )
    logger.info(
        "Admin %s broadcasted message: sent=%d, failed=%d",
        update.effective_user.id,
        sent,
        failed,
    )


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recent command to show recent downloads (admin only)."""
    if not update.message or not update.effective_user:
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("\u26d4 This command is for admins only.")
        return

    downloads = get_recent_downloads(10)

    if not downloads:
        await update.message.reply_text("\U0001f4ed No downloads recorded yet.")
        return

    text = "\U0001f4cb <b>Recent Downloads</b>\n\n"
    for d in downloads:
        user_display = d.get("username") or d.get("first_name") or str(d["user_id"])
        status_icon = "\u2705" if d["status"] == "completed" else "\u274c"
        platform = (d.get("platform") or "unknown").title()
        created = d["created_at"][:16].replace("T", " ")
        text += (
            f"{status_icon} <b>{user_display}</b>\n"
            f"   {platform} | {d.get('media_type', 'video')} | {created}\n\n"
        )

    await update.message.reply_text(text, parse_mode="HTML")


async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin command to show admin commands (admin only)."""
    if not update.message or not update.effective_user:
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("\u26d4 This command is for admins only.")
        return

    admin_text = (
        "\U0001f6e0 <b>Admin Commands</b>\n\n"
        "/stats - View bot statistics\n"
        "/ban &lt;user_id&gt; [reason] - Ban a user\n"
        "/unban &lt;user_id&gt; - Unban a user\n"
        "/broadcast &lt;message&gt; - Send message to all users\n"
        "/recent - View recent downloads\n"
        "/admin - Show this admin help\n"
    )

    await update.message.reply_text(admin_text, parse_mode="HTML")
