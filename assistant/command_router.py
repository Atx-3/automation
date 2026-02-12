"""
command_router.py — Intent-to-action routing for Clawbot.

Takes the structured JSON output from the LLM and dispatches
to the appropriate action handler. Includes confirmation flow
for dangerous operations and permission checking.
"""

import os
from typing import Optional

from file_manager import (
    read_file, list_files, get_file_path,
)
from system_control import get_system_info
from app_controller import open_app, run_safe_script
from screenshot import take_screenshot
from permissions import check_permission
import config
import database


# Actions that require user confirmation before executing
ALLOWED_ACTIONS = {
    "open_app",
    "read_file",
    "list_files",
    "send_file",
    "screenshot",
    "run_script",
    "status",
    "help",
    "chat",
}

DANGEROUS_ACTIONS = {"run_script"}

# Pending confirmations: {user_id: {action, parameters}}
_pending_confirmations: dict[int, dict] = {}


async def route_command(
    parsed: dict,
    user_id: int,
    screenshot_dir: str = "screenshots",
) -> dict:
    """
    Route a parsed LLM response to the appropriate action handler.

    Pipeline: Permission Check → Confidence Check → Confirmation → Execute

    Args:
        parsed: Dict with keys: intent, action, parameters, confidence.
        user_id: Telegram user ID (for confirmation tracking).
        screenshot_dir: Directory to save screenshots.

    Returns:
        Dict with keys:
            - text: Response message to send to user
            - file_path: Optional file to send (for send_file/screenshot)
            - needs_confirmation: True if waiting for user to confirm
    """
    action = parsed.get("action", "chat")
    params = parsed.get("parameters", {})
    confidence = parsed.get("confidence", 0.0)
    intent = parsed.get("intent", "")

    if action not in ALLOWED_ACTIONS:
        database.log_command(
            user_id=user_id,
            command=f"{action}",
            action=action,
            parameters=params,
            result="Action not allowed",
            success=False,
        )
        return {
            "text": f"🚫 Action not allowed: {action}",
            "file_path": None,
            "needs_confirmation": False,
        }

    # ── Permission Check ──────────────────────────────────────────
    if not check_permission(user_id, action):
        database.log_command(
            user_id=user_id,
            command=f"{action}",
            action=action,
            parameters=params,
            result="Permission denied",
            success=False,
        )
        return {
            "text": f"🚫 You don't have permission to perform: {action}",
            "file_path": None,
            "needs_confirmation": False,
        }

    # ── Low confidence → fall back to chat ────────────────────────
    if confidence < 0.3 and action != "chat":
        database.log_command(
            user_id=user_id,
            command=f"{action}",
            action=action,
            parameters=params,
            result="Low confidence",
            success=False,
        )
        return {
            "text": (
                f"🤔 I'm not confident enough to execute that "
                f"(confidence: {confidence:.0%}).\n"
                f"Intent: {intent}\n\n"
                f"Could you rephrase your request?"
            ),
            "file_path": None,
            "needs_confirmation": False,
        }

    # ── Dangerous action? Require confirmation ────────────────────
    if action in DANGEROUS_ACTIONS:
        _pending_confirmations[user_id] = {
            "action": action,
            "parameters": params,
        }
        desc = _describe_action(action, params)
        database.log_command(
            user_id=user_id,
            command=f"{action}",
            action=action,
            parameters=params,
            result="Confirmation required",
            success=False,
        )
        return {
            "text": (
                f"⚠️ **Confirmation Required**\n\n"
                f"Action: {desc}\n\n"
                f"Reply **YES** to confirm or **NO** to cancel."
            ),
            "file_path": None,
            "needs_confirmation": True,
        }

    # ── Execute action ────────────────────────────────────────────
    return await _execute_action(action, params, user_id, screenshot_dir)


async def handle_confirmation(
    user_id: int,
    user_reply: str,
    screenshot_dir: str = "screenshots",
) -> Optional[dict]:
    """
    Handle a YES/NO confirmation reply.

    Args:
        user_id: Telegram user ID.
        user_reply: The user's reply text.
        screenshot_dir: Directory for screenshots.

    Returns:
        Result dict if this was a confirmation, None if no pending confirmation.
    """
    if user_id not in _pending_confirmations:
        return None

    pending = _pending_confirmations.pop(user_id)
    reply = user_reply.strip().upper()

    if reply in ("YES", "Y", "CONFIRM", "DO IT", "OK", "HAAN", "HA"):
        return await _execute_action(
            pending["action"],
            pending["parameters"],
            user_id,
            screenshot_dir,
        )
    else:
        return {
            "text": "❌ Action cancelled.",
            "file_path": None,
            "needs_confirmation": False,
        }


def has_pending_confirmation(user_id: int) -> bool:
    """Check if a user has a pending action confirmation."""
    return user_id in _pending_confirmations


async def _execute_action(
    action: str,
    params: dict,
    user_id: int,
    screenshot_dir: str,
) -> dict:
    """Execute the action and return a result dict."""

    result = {"text": "", "file_path": None, "needs_confirmation": False}

    try:
        if action == "open_app":
            result["text"] = await open_app(params.get("app_name", ""))

        elif action == "read_file":
            file_path = params.get("file_path", "")
            if not file_path:
                result["text"] = "❌ Missing file_path."
            else:
                content = await read_file(file_path)
                result["text"] = f"📄 **{file_path}**\n\n{content}"

        elif action == "list_files":
            directory = params.get("directory") or (config.ALLOWED_FILE_DIRS[0] if config.ALLOWED_FILE_DIRS else ".")
            result["text"] = await list_files(directory)

        elif action == "send_file":
            file_path = params.get("file_path", "")
            valid_path = get_file_path(file_path)
            if valid_path:
                result["text"] = f"📤 Sending file: {os.path.basename(valid_path)}"
                result["file_path"] = valid_path
            else:
                result["text"] = f"❌ File not found: {file_path}"

        elif action == "screenshot":
            screenshot_path = await take_screenshot(screenshot_dir)
            if screenshot_path.startswith("ERROR:"):
                result["text"] = f"❌ Screenshot failed: {screenshot_path[6:]}"
            else:
                result["text"] = "📸 Screenshot captured!"
                result["file_path"] = screenshot_path

        elif action == "run_script":
            result["text"] = await run_safe_script(params.get("script_name", ""))

        elif action == "status":
            result["text"] = await get_system_info()

        elif action == "help":
            result["text"] = _get_help_text()

        elif action == "chat":
            result["text"] = params.get(
                "response",
                "I'm here to help! What would you like me to do?",
            )

        else:
            result["text"] = (
                f"❓ Unknown action: {action}\n"
                f"Type /help to see what I can do."
            )

        # Log to database
        database.log_command(
            user_id=user_id,
            command=f"{action}",
            action=action,
            parameters=params,
            result=result["text"][:500],
            success=not result["text"].startswith("❌"),
        )

    except Exception as e:
        result["text"] = f"❌ Error executing '{action}': {str(e)}"
        database.log_command(
            user_id=user_id,
            command=f"{action}",
            action=action,
            parameters=params,
            result=str(e),
            success=False,
        )

    return result


def _describe_action(action: str, params: dict) -> str:
    """Create a human-readable description of an action."""
    descriptions = {
        "run_script": f"📜 Run script: {params.get('script_name', 'unknown')}",
    }
    return descriptions.get(action, f"{action} with params {params}")


def _get_help_text() -> str:
    """Return the help text showing available commands."""
    return (
        "🤖 **Clawbot — Your Personal AI Assistant**\n\n"
        "Just tell me what you want in natural language! Examples:\n\n"
        "📂 **Files:**\n"
        '  • "Show me files on my Desktop"\n'
        '  • "Read the file C:\\notes.txt"\n'
        '  • "Send me the report.pdf from Documents"\n'
        "\n"
        "🖥️ **System:**\n"
        '  • "Open Chrome"\n'
        '  • "Open Notepad"\n'
        '  • "Take a screenshot"\n'
        "\n"
        "📜 **Scripts:**\n"
        '  • "Run the backup script"\n\n'
        "📋 **Commands:**\n"
        "  /start — Start Clawbot\n"
        "  /help — This help menu\n"
        "  /status — System status\n"
        "  /screenshot — Quick screenshot\n"
    )
