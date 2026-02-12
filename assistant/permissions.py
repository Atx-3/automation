"""
permissions.py — Role-based access control for Chapna AI Assistant.

Defines user roles and maps permissions to actions.
Owner role has full access to all actions.
"""

from enum import Enum
from typing import Optional

import config


class UserRole(Enum):
    """User roles with increasing privilege levels."""
    NONE = 0       # Unauthorized — no access
    VIEWER = 1     # Can view status, help, chat only
    OPERATOR = 2   # Can read files, take screenshots, system info
    OWNER = 3      # Full access — all actions


# ── Permission Matrix ─────────────────────────────────────────────────
# Maps each action to the minimum role required
ACTION_PERMISSIONS: dict[str, UserRole] = {
    # Everyone (viewer+)
    "chat": UserRole.VIEWER,
    "help": UserRole.VIEWER,
    "status": UserRole.VIEWER,

    # Operator+
    "read_file": UserRole.OPERATOR,
    "list_files": UserRole.OPERATOR,
    "search_files": UserRole.OPERATOR,
    "screenshot": UserRole.OPERATOR,
    "system_info": UserRole.OPERATOR,

    # Owner only
    "open_app": UserRole.OWNER,
    "run_command": UserRole.OWNER,
    "write_file": UserRole.OWNER,
    "delete_file": UserRole.OWNER,
    "send_file": UserRole.OWNER,
    "send_message": UserRole.OWNER,
    "kill_process": UserRole.OWNER,
    "run_script": UserRole.OWNER,
    "shutdown": UserRole.OWNER,
    "restart": UserRole.OWNER,
    "lock": UserRole.OWNER,
    "volume": UserRole.OWNER,
}


def get_user_role(user_id: int) -> UserRole:
    """
    Determine the role for a given Telegram user ID.

    All users in TELEGRAM_ALLOWED_USER_IDS get OWNER role.
    Unknown users get NONE.

    Args:
        user_id: Telegram user ID.

    Returns:
        The user's role.
    """
    if user_id in config.TELEGRAM_ALLOWED_USER_IDS:
        return UserRole.OWNER
    return UserRole.NONE


def check_permission(user_id: int, action: str) -> bool:
    """
    Check if a user has permission to execute an action.

    Args:
        user_id: Telegram user ID.
        action: The action name to check.

    Returns:
        True if the user has sufficient role for the action.
    """
    user_role = get_user_role(user_id)
    required_role = ACTION_PERMISSIONS.get(action, UserRole.OWNER)
    return user_role.value >= required_role.value


def get_allowed_actions(user_id: int) -> list[str]:
    """
    Get all actions a user is allowed to perform.

    Args:
        user_id: Telegram user ID.

    Returns:
        List of action names the user can execute.
    """
    user_role = get_user_role(user_id)
    return [
        action for action, required in ACTION_PERMISSIONS.items()
        if user_role.value >= required.value
    ]
