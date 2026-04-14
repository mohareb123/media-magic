"""SQLite database management for the bot."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Generator

from bot.config import DB_PATH
from bot.utils.logger import logger


def _ensure_db_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection as a context manager."""
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database with required tables."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                total_downloads INTEGER DEFAULT 0,
                language_code TEXT
            );

            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                platform TEXT,
                media_type TEXT,
                quality TEXT,
                file_size INTEGER,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                added_by INTEGER,
                is_active INTEGER DEFAULT 1,
                added_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_user_id INTEGER,
                details TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_downloads_user_id ON downloads(user_id);
            CREATE INDEX IF NOT EXISTS idx_downloads_created_at ON downloads(created_at);
            CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status);
        """)
    logger.info("Database initialized successfully")


def upsert_user(
    user_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    language_code: str | None = None,
) -> None:
    """Insert or update a user record."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, last_name, language_code, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                language_code = excluded.language_code,
                last_seen = excluded.last_seen
            """,
            (user_id, username, first_name, last_name, language_code, now, now),
        )


def is_user_banned(user_id: int) -> bool:
    """Check if a user is banned."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT is_banned FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return bool(row and row["is_banned"])


def ban_user(user_id: int, reason: str = "") -> bool:
    """Ban a user. Returns True if successful."""
    with get_connection() as conn:
        result = conn.execute(
            "UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?",
            (reason, user_id),
        )
        return result.rowcount > 0


def unban_user(user_id: int) -> bool:
    """Unban a user. Returns True if successful."""
    with get_connection() as conn:
        result = conn.execute(
            "UPDATE users SET is_banned = 0, ban_reason = NULL WHERE user_id = ?",
            (user_id,),
        )
        return result.rowcount > 0


def record_download(
    user_id: int,
    url: str,
    platform: str | None = None,
    media_type: str = "video",
    quality: str = "best",
) -> int:
    """Record a new download attempt. Returns the download ID."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO downloads (user_id, url, platform, media_type, quality, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (user_id, url, platform, media_type, quality, now),
        )
        return cursor.lastrowid  # type: ignore[return-value]


def update_download_status(
    download_id: int,
    status: str,
    file_size: int | None = None,
    error_message: str | None = None,
) -> None:
    """Update download status."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE downloads
            SET status = ?, file_size = ?, error_message = ?, completed_at = ?
            WHERE id = ?
            """,
            (status, file_size, error_message, now, download_id),
        )
        if status == "completed":
            row = conn.execute(
                "SELECT user_id FROM downloads WHERE id = ?", (download_id,)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE users SET total_downloads = total_downloads + 1 WHERE user_id = ?",
                    (row["user_id"],),
                )


def get_user_download_count_today(user_id: int) -> int:
    """Get the number of downloads a user has made today."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) as count FROM downloads
            WHERE user_id = ? AND created_at >= ? AND status = 'completed'
            """,
            (user_id, today_start),
        ).fetchone()
        return row["count"] if row else 0


def get_stats() -> dict[str, Any]:
    """Get overall bot statistics."""
    with get_connection() as conn:
        total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        active_users_7d = conn.execute(
            "SELECT COUNT(*) as c FROM users WHERE last_seen >= ?",
            ((datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),),
        ).fetchone()["c"]
        total_downloads = conn.execute(
            "SELECT COUNT(*) as c FROM downloads WHERE status = 'completed'"
        ).fetchone()["c"]
        downloads_today = conn.execute(
            "SELECT COUNT(*) as c FROM downloads WHERE status = 'completed' AND created_at >= ?",
            (
                datetime.now(timezone.utc)
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .isoformat(),
            ),
        ).fetchone()["c"]
        banned_users = conn.execute(
            "SELECT COUNT(*) as c FROM users WHERE is_banned = 1"
        ).fetchone()["c"]
        total_groups = conn.execute(
            "SELECT COUNT(*) as c FROM groups WHERE is_active = 1"
        ).fetchone()["c"]
        platform_stats_rows = conn.execute(
            """
            SELECT platform, COUNT(*) as c FROM downloads
            WHERE status = 'completed' AND platform IS NOT NULL
            GROUP BY platform ORDER BY c DESC
            """
        ).fetchall()
        platform_stats = {row["platform"]: row["c"] for row in platform_stats_rows}

        return {
            "total_users": total_users,
            "active_users_7d": active_users_7d,
            "total_downloads": total_downloads,
            "downloads_today": downloads_today,
            "banned_users": banned_users,
            "total_groups": total_groups,
            "platform_stats": platform_stats,
        }


def get_recent_downloads(limit: int = 10) -> list[dict[str, Any]]:
    """Get recent download records."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT d.*, u.username, u.first_name
            FROM downloads d
            LEFT JOIN users u ON d.user_id = u.user_id
            ORDER BY d.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_all_user_ids() -> list[int]:
    """Get all non-banned user IDs for broadcasting."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT user_id FROM users WHERE is_banned = 0"
        ).fetchall()
        return [row["user_id"] for row in rows]


def add_group(chat_id: int, title: str, added_by: int) -> None:
    """Record a group the bot was added to."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO groups (chat_id, title, added_by, added_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                is_active = 1
            """,
            (chat_id, title, added_by, now),
        )


def remove_group(chat_id: int) -> None:
    """Mark a group as inactive."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE groups SET is_active = 0 WHERE chat_id = ?", (chat_id,)
        )


def log_admin_action(
    admin_id: int,
    action: str,
    target_user_id: int | None = None,
    details: str = "",
) -> None:
    """Log an admin action."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO admin_logs (admin_id, action, target_user_id, details, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (admin_id, action, target_user_id, details, now),
        )
