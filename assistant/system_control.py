"""
system_control.py — System command execution and process management.

Provides full shell command execution, application launching,
process management, and system information retrieval.
"""

import os
import subprocess
import platform
import psutil
from typing import Optional


# Common Windows applications and their paths/commands
COMMON_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "terminal": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "control panel": "control.exe",
    "settings": "ms-settings:",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "vscode": "code",
    "vs code": "code",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "outlook": "outlook.exe",
    "spotify": os.path.expandvars(
        r"%APPDATA%\Spotify\Spotify.exe"
    ),
    "discord": os.path.expandvars(
        r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe"
    ),
    "telegram": os.path.expandvars(
        r"%APPDATA%\Telegram Desktop\Telegram.exe"
    ),
    "whatsapp": "explorer.exe shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
}


async def open_app(app_name: str) -> str:
    """
    Open an application by name.

    Args:
        app_name: Name of the application (case-insensitive).

    Returns:
        Success or error message.
    """
    try:
        app_key = app_name.lower().strip()
        app_path = COMMON_APPS.get(app_key)

        if app_path:
            # Handle ms-settings: protocol
            if app_path.startswith("ms-settings:"):
                os.startfile(app_path)
                return f"✅ Opened: {app_name}"

            # Handle commands with arguments
            if " " in app_path and not os.path.exists(app_path):
                parts = app_path.split(" ", 1)
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

            return f"✅ Opened: {app_name}"

        # Try to open as a program name directly
        try:
            subprocess.Popen(
                [app_name],
                shell=False,
                creationflags=subprocess.DETACHED_PROCESS,
            )
            return f"✅ Opened: {app_name}"
        except FileNotFoundError:
            # Try os.startfile as last resort (works for URLs and registered types)
            try:
                os.startfile(app_name)
                return f"✅ Opened: {app_name}"
            except Exception:
                return (
                    f"❌ Could not find application: {app_name}\n"
                    f"💡 Known apps: {', '.join(sorted(COMMON_APPS.keys()))}"
                )

    except Exception as e:
        return f"❌ Error opening {app_name}: {str(e)}"


async def run_command(command: str, timeout: int = 60) -> str:
    """
    Execute a shell command and return the output.

    Args:
        command: The command to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        Command output (stdout + stderr) or error message.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.expanduser("~"),
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"

        if not output.strip():
            output = f"✅ Command executed successfully (exit code: {result.returncode})"
        else:
            # Truncate for Telegram
            if len(output) > 3800:
                output = output[:3800] + f"\n\n... [output truncated]"
            output = f"```\n{output.strip()}\n```"

        return output

    except subprocess.TimeoutExpired:
        return f"⏰ Command timed out after {timeout} seconds."
    except Exception as e:
        return f"❌ Error executing command: {str(e)}"


async def kill_process(process_name: str) -> str:
    """
    Kill a running process by name.

    Args:
        process_name: Name of the process to kill.

    Returns:
        Success or error message.
    """
    try:
        killed = 0
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                if process_name.lower() in proc.info["name"].lower():
                    proc.terminate()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed > 0:
            return f"✅ Terminated {killed} process(es) matching '{process_name}'"
        else:
            return f"❌ No running process found matching '{process_name}'"

    except Exception as e:
        return f"❌ Error killing process: {str(e)}"


async def get_system_info() -> str:
    """
    Get comprehensive system information.

    Returns:
        Formatted system info string.
    """
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        # Memory
        mem = psutil.virtual_memory()

        # Disk
        disk = psutil.disk_usage("C:\\")

        # Network
        net = psutil.net_if_addrs()
        ip_addresses = []
        for iface, addrs in net.items():
            for addr in addrs:
                if addr.family.name == "AF_INET" and not addr.address.startswith("127."):
                    ip_addresses.append(f"{iface}: {addr.address}")

        # Battery (if laptop)
        battery = psutil.sensors_battery()
        battery_info = ""
        if battery:
            battery_info = (
                f"\n🔋 **Battery:** {battery.percent}% "
                f"({'Charging' if battery.power_plugged else 'On Battery'})"
            )

        # Uptime
        boot_time = psutil.boot_time()
        import datetime
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time)
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes = remainder // 60

        info = (
            f"💻 **System Information**\n\n"
            f"🖥️ **OS:** {platform.system()} {platform.release()} ({platform.version()})\n"
            f"🏗️ **Architecture:** {platform.machine()}\n"
            f"👤 **User:** {os.getenv('USERNAME', 'Unknown')}\n"
            f"⏱️ **Uptime:** {hours}h {minutes}m\n\n"
            f"⚡ **CPU:** {cpu_percent}% usage ({cpu_count} cores"
            f"{f', {cpu_freq.current:.0f} MHz' if cpu_freq else ''})\n"
            f"🧠 **RAM:** {mem.percent}% used "
            f"({mem.used / 1024**3:.1f} / {mem.total / 1024**3:.1f} GB)\n"
            f"💾 **Disk C:** {disk.percent}% used "
            f"({disk.used / 1024**3:.1f} / {disk.total / 1024**3:.1f} GB)\n"
            f"{battery_info}\n\n"
            f"🌐 **Network:**\n"
            + "\n".join(f"  • {ip}" for ip in ip_addresses[:5])
        )

        return info

    except Exception as e:
        return f"❌ Error getting system info: {str(e)}"
