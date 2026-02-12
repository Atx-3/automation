"""
app_controller.py — Application launching and system control for Chapna.

Handles:
- Opening applications from the whitelist
- Running predefined safe scripts
- System actions (lock, shutdown, restart, sleep)
- Volume control
"""

import os
import subprocess
import ctypes
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

        if app_path:
            # Handle ms-settings: protocol
            if app_path.startswith("ms-settings:"):
                os.startfile(app_path)
                logger.info(f"Opened app: {app_name} ({app_path})")
                return f"✅ Opened: {app_name}"

            # Handle commands with arguments (e.g., Discord's update.exe)
            if " " in app_path and not os.path.exists(app_path):
                subprocess.Popen(
                    app_path,
                    shell=False,
                    creationflags=subprocess.DETACHED_PROCESS,
                )
            else:
                subprocess.Popen(
                    [app_path],
                    shell=False,
                    creationflags=subprocess.DETACHED_PROCESS,
                )

            logger.info(f"Opened app: {app_name} ({app_path})")
            return f"✅ Opened: {app_name}"

        # Try to open as a program name directly
        try:
            subprocess.Popen(
                [app_name],
                shell=False,
                creationflags=subprocess.DETACHED_PROCESS,
            )
            logger.info(f"Opened app directly: {app_name}")
            return f"✅ Opened: {app_name}"
        except FileNotFoundError:
            # Try os.startfile as last resort
            try:
                os.startfile(app_name)
                logger.info(f"Opened via startfile: {app_name}")
                return f"✅ Opened: {app_name}"
            except Exception:
                known = ", ".join(sorted(config.WHITELISTED_APPS.keys()))
                return (
                    f"❌ Could not find application: {app_name}\n"
                    f"💡 Known apps: {known}"
                )

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


async def lock_screen() -> str:
    """Lock the Windows screen."""
    try:
        ctypes.windll.user32.LockWorkStation()
        logger.info("Screen locked")
        return "🔒 PC screen locked."
    except Exception as e:
        return f"❌ Could not lock screen: {str(e)}"


async def system_power(action: str) -> str:
    """
    Shutdown, restart, or sleep the PC.

    Args:
        action: One of 'shutdown', 'restart', 'sleep'.

    Returns:
        Status message.
    """
    action = action.lower().strip()

    try:
        if action == "shutdown":
            subprocess.Popen(["shutdown", "/s", "/t", "30"], creationflags=subprocess.DETACHED_PROCESS)
            logger.info("Shutdown initiated (30s delay)")
            return "⚠️ PC will shut down in 30 seconds.\nRun `shutdown /a` to cancel."

        elif action == "restart":
            subprocess.Popen(["shutdown", "/r", "/t", "30"], creationflags=subprocess.DETACHED_PROCESS)
            logger.info("Restart initiated (30s delay)")
            return "⚠️ PC will restart in 30 seconds.\nRun `shutdown /a` to cancel."

        elif action == "sleep":
            subprocess.Popen(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                creationflags=subprocess.DETACHED_PROCESS,
            )
            logger.info("Sleep initiated")
            return "😴 PC is going to sleep."

        else:
            return f"❌ Unknown power action: {action}\n💡 Use: shutdown, restart, or sleep"

    except Exception as e:
        logger.error(f"Power action error: {e}")
        return f"❌ Error: {str(e)}"


async def control_volume(level: str) -> str:
    """
    Control system volume.

    Args:
        level: 'up', 'down', 'mute', 'unmute', or a number 0-100.

    Returns:
        Status message.
    """
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        level_str = level.lower().strip()

        if level_str == "mute":
            volume.SetMute(1, None)
            return "🔇 Volume muted."
        elif level_str == "unmute":
            volume.SetMute(0, None)
            return "🔊 Volume unmuted."
        elif level_str == "up":
            current = volume.GetMasterVolumeLevelScalar()
            new_level = min(1.0, current + 0.1)
            volume.SetMasterVolumeLevelScalar(new_level, None)
            return f"🔊 Volume up: {int(new_level * 100)}%"
        elif level_str == "down":
            current = volume.GetMasterVolumeLevelScalar()
            new_level = max(0.0, current - 0.1)
            volume.SetMasterVolumeLevelScalar(new_level, None)
            return f"🔉 Volume down: {int(new_level * 100)}%"
        else:
            try:
                pct = int(level_str)
                pct = max(0, min(100, pct))
                volume.SetMasterVolumeLevelScalar(pct / 100.0, None)
                return f"🔊 Volume set to {pct}%"
            except ValueError:
                return f"❌ Invalid volume level: {level}\n💡 Use: up, down, mute, unmute, or 0-100"

    except ImportError:
        return (
            "❌ Volume control requires `pycaw`. Install it:\n"
            "`pip install pycaw comtypes`"
        )
    except Exception as e:
        return f"❌ Volume error: {str(e)}"
