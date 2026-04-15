"""Logging configuration for the bot."""

import logging
import sys
from logging.handlers import RotatingFileHandler

from bot.config import LOG_DIR, LOG_FILE


def setup_logger() -> logging.Logger:
    """Set up and return the bot logger with file and console handlers."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("media_magic_bot")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()
