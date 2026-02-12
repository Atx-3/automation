"""
screenshot.py — Screen capture module for the AI Assistant.

Captures the full screen and saves it as a PNG file.
Includes auto-cleanup of old screenshots.
"""

import os
import time
import glob
from datetime import datetime
from PIL import ImageGrab


async def take_screenshot(save_dir: str = "screenshots") -> str:
    """
    Capture the full screen and save as a PNG file.

    Args:
        save_dir: Directory to save screenshots in.

    Returns:
        Absolute path to the saved screenshot, or error message.
    """
    try:
        # Ensure save directory exists
        os.makedirs(save_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(os.path.abspath(save_dir), filename)

        # Capture the screen
        screenshot = ImageGrab.grab()
        screenshot.save(filepath, "PNG")

        # Cleanup old screenshots (keep last 20)
        _cleanup_old_screenshots(save_dir, keep=20)

        return filepath

    except Exception as e:
        return f"ERROR:{str(e)}"


def _cleanup_old_screenshots(save_dir: str, keep: int = 20) -> None:
    """
    Remove old screenshots, keeping only the most recent ones.

    Args:
        save_dir: Directory containing screenshots.
        keep: Number of recent screenshots to keep.
    """
    try:
        pattern = os.path.join(save_dir, "screenshot_*.png")
        files = sorted(glob.glob(pattern), key=os.path.getmtime)

        # Delete oldest files if we have more than 'keep'
        if len(files) > keep:
            for old_file in files[: len(files) - keep]:
                try:
                    os.remove(old_file)
                except OSError:
                    pass
    except Exception:
        pass  # Non-critical operation
