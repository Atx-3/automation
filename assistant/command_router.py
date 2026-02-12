"""
command_router.py — Intent-to-action routing for the AI Assistant.

Takes the structured JSON output from the LLM and dispatches
to the appropriate action handler. Includes confirmation flow
for dangerous operations.
"""

import os
from typing import Optional, Callable, Any

from file_manager import (
    read_file, write_file, delete_file,
    list_files, search_files, get_file_path,
)
from system_control import (
    open_app, run_command, kill_process, get_system_info,
)
from screenshot import take_screenshot
from messaging import send_message

# Actions that require user confirmation before executing
DANGEROUS_ACTIONS = {"delete_file", "kill_process"}

# Pending confirmations: {user_id: {action, parameters}}
_pending_confirmations: dict[int, dict] = {}


async def route_command(
    parsed: dict,
    user_id: int,
    screenshot_dir: str = "screenshots",
) -> dict:
    """
    Route a parsed LLM response to the appropriate action handler.

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

    # Low confidence → fall back to chat
    if confidence < 0.3 and action != "chat":
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
    return await _execute_action(action, params, screenshot_dir)


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

    if reply in ("YES", "Y", "CONFIRM", "DO IT", "OK"):
        return await _execute_action(
            pending["action"],
            pending["parameters"],
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
    screenshot_dir: str,
) -> dict:
    """Execute the action and return a result dict."""

    result = {"text": "", "file_path": None, "needs_confirmation": False}

    try:
        if action == "open_app":
            result["text"] = await open_app(params.get("app_name", ""))

        elif action == "run_command":
            result["text"] = await run_command(params.get("command", ""))

        elif action == "read_file":
            content = await read_file(params.get("file_path", ""))
            result["text"] = f"📄 **{params.get('file_path', '')}**\n\n{content}"

        elif action == "write_file":
            result["text"] = await write_file(
                params.get("file_path", ""),
                params.get("content", ""),
            )

        elif action == "delete_file":
            result["text"] = await delete_file(params.get("file_path", ""))

        elif action == "list_files":
            result["text"] = await list_files(params.get("directory", "."))

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

        elif action == "system_info":
            result["text"] = await get_system_info()

        elif action == "send_message":
            result["text"] = await send_message(
                platform=params.get("platform", ""),
                to=params.get("to", ""),
                subject=params.get("subject", ""),
                body=params.get("body", ""),
            )

        elif action == "kill_process":
            result["text"] = await kill_process(params.get("process_name", ""))

        elif action == "search_files":
            result["text"] = await search_files(
                query=params.get("query", ""),
                directory=params.get("directory", "C:\\"),
            )

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

    except Exception as e:
        result["text"] = f"❌ Error executing '{action}': {str(e)}"

    return result


def _describe_action(action: str, params: dict) -> str:
    """Create a human-readable description of an action."""
    if action == "delete_file":
        return f"🗑️ Delete file: {params.get('file_path', 'unknown')}"
    elif action == "kill_process":
        return f"💀 Kill process: {params.get('process_name', 'unknown')}"
    return f"{action} with params {params}"


def _get_help_text() -> str:
    """Return the help text showing available commands."""
    return (
        "🤖 **AI Assistant — Help**\n\n"
        "Just tell me what you want in natural language! Examples:\n\n"
        "📂 **Files:**\n"
        '  • "Show me files on my Desktop"\n'
        '  • "Read the file C:\\notes.txt"\n'
        '  • "Send me the report.pdf from Documents"\n'
        '  • "Create a file called test.txt with Hello World"\n'
        '  • "Delete old_file.txt"\n'
        '  • "Search for .py files in my projects"\n\n'
        "🖥️ **System:**\n"
        '  • "Open Chrome"\n'
        '  • "Open Notepad"\n'
        '  • "Run dir command"\n'
        '  • "Show system info"\n'
        '  • "Kill notepad process"\n'
        '  • "Take a screenshot"\n\n'
        "📧 **Messaging:**\n"
        '  • "Send an email to john@email.com"\n\n'
        "📋 **Commands:**\n"
        "  • /start — Start the bot\n"
        "  • /help — Show this help\n"
        "  • /status — System status\n"
        "  • /screenshot — Quick screenshot\n"
    )
