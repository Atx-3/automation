"""
system_control.py — System command execution and process management for Chapna.

Provides shell command execution, process management,
and system information retrieval.
"""

import os
import subprocess
import platform
import psutil
from typing import Optional

from logger import setup_logger
import config

logger = setup_logger("system", config.LOG_FILE, config.LOG_LEVEL)


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
        logger.info(f"Executing command: {command}")

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

        logger.info(f"Command exit code: {result.returncode}")
        return output

    except subprocess.TimeoutExpired:
        return f"⏰ Command timed out after {timeout} seconds."
    except Exception as e:
        logger.error(f"Command error: {e}")
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
            logger.info(f"Killed {killed} process(es): {process_name}")
            return f"✅ Terminated {killed} process(es) matching '{process_name}'"
        else:
            return f"❌ No running process found matching '{process_name}'"

    except Exception as e:
        logger.error(f"Kill process error: {e}")
        return f"❌ Error killing process: {str(e)}"


async def get_system_info() -> str:
    """
    Get comprehensive system information.

    Returns:
        Formatted system info string.
    """
    try:
        import datetime

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
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time)
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes = remainder // 60

        # Running processes count
        proc_count = len(list(psutil.process_iter()))

        info = (
            f"💻 **Chapna System Report**\n\n"
            f"🖥️ **OS:** {platform.system()} {platform.release()} ({platform.version()})\n"
            f"🏗️ **Architecture:** {platform.machine()}\n"
            f"👤 **User:** {os.getenv('USERNAME', 'Unknown')}\n"
            f"⏱️ **Uptime:** {hours}h {minutes}m\n"
            f"⚙️ **Processes:** {proc_count} running\n\n"
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
