"""
system_control.py — System information utilities for Chapna.
"""

import os
import platform
import psutil
from typing import Optional

from logger import setup_logger
import config

logger = setup_logger("system", config.LOG_FILE, config.LOG_LEVEL)


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
