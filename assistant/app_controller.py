"""
app_controller.py — Application launching and safe script execution for Chapna.
"""

import os
import subprocess
import shlex
from typing import Optional

import config
from logger import setup_logger

logger = setup_logger("app_ctrl", config.LOG_FILE, config.LOG_LEVEL)


async def open_app(app_name: str) -> str:
    """
    Open an application by name.

    Checks the whitelist first, then tries to launch directly.

    Args:
        app_name: Name of the application (case-insensitive).

    Returns:
        Success or error message.
    """
    try:
        app_key = app_name.lower().strip()
        app_path = config.WHITELISTED_APPS.get(app_key)

        if not app_path:
            known = ", ".join(sorted(config.WHITELISTED_APPS.keys()))
            return (
                f"❌ Application not allowed: {app_name}\n"
                f"✅ Allowed apps: {known}"
            )

        if isinstance(app_path, (list, tuple)):
            cmd = list(app_path)
        else:
            if app_path.startswith("ms-settings:"):
                os.startfile(app_path)
                logger.info(f"Opened app: {app_name} ({app_path})")
                return f"✅ Opened: {app_name}"
            if os.path.exists(app_path):
                cmd = [app_path]
            else:
                cmd = shlex.split(app_path, posix=False)

        subprocess.Popen(
            cmd,
            shell=False,
            creationflags=subprocess.DETACHED_PROCESS,
        )

        logger.info(f"Opened app: {app_name} ({app_path})")
        return f"✅ Opened: {app_name}"

    except Exception as e:
        logger.error(f"Error opening app {app_name}: {e}")
        return f"❌ Error opening {app_name}: {str(e)}"


async def run_safe_script(script_name: str) -> str:
    """
    Run a predefined safe script from config.

    Args:
        script_name: Name of the script (must be in SAFE_SCRIPTS config).

    Returns:
        Script output or error message.
    """
    script_key = script_name.lower().strip()
    script_path = config.SAFE_SCRIPTS.get(script_key)

    if not script_path:
        available = ", ".join(config.SAFE_SCRIPTS.keys()) or "None configured"
        return (
            f"❌ Unknown script: {script_name}\n"
            f"📜 Available scripts: {available}\n\n"
            f"💡 Add scripts in config.py → SAFE_SCRIPTS"
        )

    if not os.path.isfile(script_path):
        return f"❌ Script file not found: {script_path}"

    try:
        script_path = os.path.abspath(script_path)
        scripts_root = os.path.abspath(config.SCRIPTS_DIR)
        if os.path.commonpath([script_path, scripts_root]) != scripts_root:
            return "❌ Script path is outside the allowed scripts directory."
    except Exception:
        return "❌ Script path validation failed."

    try:
        # Determine how to run the script
        ext = os.path.splitext(script_path)[1].lower()
        if ext == ".ps1":
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path]
        elif ext == ".bat" or ext == ".cmd":
            cmd = ["cmd", "/c", script_path]
        elif ext == ".py":
            cmd = ["python", script_path]
        else:
            return f"❌ Unsupported script type: {ext}"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(script_path),
        )

        output = result.stdout or ""
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"

        if not output.strip():
            output = f"✅ Script '{script_name}' executed (exit code: {result.returncode})"
        else:
            if len(output) > 3800:
                output = output[:3800] + "\n\n... [truncated]"
            output = f"📜 Script '{script_name}' output:\n```\n{output.strip()}\n```"

        logger.info(f"Ran script: {script_name} → exit code {result.returncode}")
        return output

    except subprocess.TimeoutExpired:
        return f"⏰ Script '{script_name}' timed out after 120 seconds."
    except Exception as e:
        logger.error(f"Script error: {e}")
        return f"❌ Error running script: {str(e)}"


