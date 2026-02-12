"""
database.py — Local SQLite database for Chapna AI Assistant.

Stores conversation history, command logs, and user preferences
entirely on the local machine. No cloud dependency.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Optional

import config


# Database file path — stored alongside the assistant
DB_PATH = os.path.join(config.BASE_DIR, "chapna.db")


def get_connection() -> sqlite3.Connection:
    """
    Get a SQLite connection with row factory enabled.

    Returns:
        sqlite3.Connection instance.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # Better concurrency
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database() -> None:
    """
    Initialize the database schema. Creates tables if they don't exist.
    Safe to call multiple times.
    """
    conn = get_connection()
    try:
        conn.executescript("""
            -- Conversation history for context memory
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                role        TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                message     TEXT NOT NULL,
                action      TEXT DEFAULT NULL,
                timestamp   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            -- Command execution audit log
            CREATE TABLE IF NOT EXISTS command_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                command     TEXT NOT NULL,
                action      TEXT NOT NULL,
                parameters  TEXT DEFAULT '{}',
                result      TEXT DEFAULT '',
                success     INTEGER NOT NULL DEFAULT 1,
                timestamp   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            -- User preferences and settings
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id     INTEGER PRIMARY KEY,
                nickname    TEXT DEFAULT '',
                preferences TEXT DEFAULT '{}',
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            -- Notes and reminders
            CREATE TABLE IF NOT EXISTS notes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                title       TEXT NOT NULL,
                content     TEXT DEFAULT '',
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            -- Create indexes for fast lookups
            CREATE INDEX IF NOT EXISTS idx_conv_user
                ON conversations(user_id, timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_logs_user
                ON command_logs(user_id, timestamp DESC);
        """)
        conn.commit()
    finally:
        conn.close()


# ── Conversation History ──────────────────────────────────────────────

def save_message(user_id: int, role: str, message: str, action: str = None) -> None:
    """
    Save a conversation message.

    Args:
        user_id: Telegram user ID.
        role: 'user' or 'assistant'.
        message: The message text.
        action: Optional action name for assistant messages.
    """
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO conversations (user_id, role, message, action) VALUES (?, ?, ?, ?)",
            (user_id, role, message[:10000], action),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_messages(user_id: int, limit: int = 20) -> list[dict]:
    """
    Get recent conversation history for context.

    Args:
        user_id: Telegram user ID.
        limit: Maximum number of messages to retrieve.

    Returns:
        List of message dicts with role, message, timestamp keys.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT role, message, action, timestamp FROM conversations "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        # Reverse to chronological order
        return [dict(row) for row in reversed(rows)]
    finally:
        conn.close()


def clear_history(user_id: int) -> int:
    """
    Clear conversation history for a user.

    Returns:
        Number of messages deleted.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM conversations WHERE user_id = ?", (user_id,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# ── Command Logs ──────────────────────────────────────────────────────

def log_command(
    user_id: int,
    command: str,
    action: str,
    parameters: dict = None,
    result: str = "",
    success: bool = True,
) -> None:
    """
    Log a command execution to the database.

    Args:
        user_id: Telegram user ID.
        command: Raw user command text.
        action: Resolved action name.
        parameters: Action parameters dict.
        result: Execution result summary.
        success: Whether the command succeeded.
    """
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO command_logs (user_id, command, action, parameters, result, success) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                command[:2000],
                action,
                json.dumps(parameters or {}),
                result[:5000],
                1 if success else 0,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_command_stats(user_id: int) -> dict:
    """
    Get command usage statistics for a user.

    Returns:
        Dict with total_commands, success_count, top_actions.
    """
    conn = get_connection()
    try:
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM command_logs WHERE user_id = ?",
            (user_id,),
        ).fetchone()["cnt"]

        success = conn.execute(
            "SELECT COUNT(*) as cnt FROM command_logs WHERE user_id = ? AND success = 1",
            (user_id,),
        ).fetchone()["cnt"]

        top_actions = conn.execute(
            "SELECT action, COUNT(*) as cnt FROM command_logs "
            "WHERE user_id = ? GROUP BY action ORDER BY cnt DESC LIMIT 5",
            (user_id,),
        ).fetchall()

        return {
            "total_commands": total,
            "success_count": success,
            "failure_count": total - success,
            "top_actions": [{"action": r["action"], "count": r["cnt"]} for r in top_actions],
        }
    finally:
        conn.close()


# ── User Settings ─────────────────────────────────────────────────────

def get_user_setting(user_id: int, key: str, default=None):
    """
    Get a user preference value.

    Args:
        user_id: Telegram user ID.
        key: Preference key.
        default: Default value if not found.

    Returns:
        The stored value or default.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT preferences FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row:
            prefs = json.loads(row["preferences"])
            return prefs.get(key, default)
        return default
    finally:
        conn.close()


def set_user_setting(user_id: int, key: str, value) -> None:
    """
    Set a user preference value.

    Args:
        user_id: Telegram user ID.
        key: Preference key.
        value: Value to store (must be JSON-serializable).
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT preferences FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if row:
            prefs = json.loads(row["preferences"])
            prefs[key] = value
            conn.execute(
                "UPDATE user_settings SET preferences = ?, updated_at = datetime('now', 'localtime') "
                "WHERE user_id = ?",
                (json.dumps(prefs), user_id),
            )
        else:
            prefs = {key: value}
            conn.execute(
                "INSERT INTO user_settings (user_id, preferences) VALUES (?, ?)",
                (user_id, json.dumps(prefs)),
            )
        conn.commit()
    finally:
        conn.close()


# ── Notes ─────────────────────────────────────────────────────────────

def save_note(user_id: int, title: str, content: str = "") -> int:
    """
    Save a note.

    Returns:
        The note ID.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
            (user_id, title, content),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_notes(user_id: int, limit: int = 20) -> list[dict]:
    """Get recent notes for a user."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, content, created_at FROM notes "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_note(user_id: int, note_id: int) -> bool:
    """Delete a note by ID. Returns True if deleted."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM notes WHERE id = ? AND user_id = ?",
            (note_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
