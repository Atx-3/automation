"""
logger.py — Structured logging for Chapna AI Assistant.

Provides rotating file logs + console output with timestamps,
user context, action tracking, and security event reporting.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logger(
    name: str = "chapna",
    log_file: str = "chapna.log",
    level: str = "INFO",
) -> logging.Logger:
    """
    Create and configure a logger with both console and file handlers.

    Args:
        name: Logger name identifier.
        log_file: Path to the log file.
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # ── Format ────────────────────────────────────────────────────
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-12s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Console Handler ──────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ── Rotating File Handler (5 MB max, 5 backups) ──────────────
    try:
        log_dir = os.path.dirname(os.path.abspath(log_file))
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not set up file logging: {e}")

    return logger


def log_command(
    logger: logging.Logger,
    user_id: int,
    command: str,
    action: str = "",
    result: str = "",
    error: str = "",
) -> None:
    """
    Log a structured command entry for audit trail.

    Args:
        logger: Logger instance.
        user_id: Telegram user ID.
        command: The raw command text.
        action: The resolved action name.
        result: The execution result summary.
        error: Error message if any.
    """
    log_entry = (
        f"[CMD] user={user_id} | command=\"{command[:200]}\" | "
        f"action={action} | result=\"{result[:200]}\" | error=\"{error}\""
    )
    if error:
        logger.error(log_entry)
    else:
        logger.info(log_entry)


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    user_id: int,
    details: str = "",
) -> None:
    """
    Log a security-relevant event.

    Args:
        logger: Logger instance.
        event_type: Type of event (AUTH_FAIL, RATE_LIMIT, BLOCKED, etc.)
        user_id: Telegram user ID.
        details: Additional context.
    """
    logger.warning(
        f"[SECURITY] {event_type} | user={user_id} | {details}"
    )
