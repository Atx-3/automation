"""
file_manager.py — Full file system access for Chapna AI Assistant.

Provides read, write, delete, list, search, and send capabilities
for files on the PC.
"""

import os
import glob
from typing import Optional

import config


async def read_file(file_path: str) -> str:
    """
    Read the contents of a file.

    Args:
        file_path: Absolute path to the file.

    Returns:
        File contents as string, or error message.
    """
    try:
        file_path = _normalize_path(file_path)
        if not _is_path_allowed(file_path):
            return "❌ Access denied: path is outside allowed directories."

        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"

        if not os.path.isfile(file_path):
            return f"❌ Not a file: {file_path}"

        # Check file size (limit to 10 MB for text reading)
        size = os.path.getsize(file_path)
        if size > 10 * 1024 * 1024:
            return (
                f"⚠️ File is too large to read as text ({size / 1024 / 1024:.1f} MB). "
                f"Use 'send_file' to download it instead."
            )

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Truncate for Telegram message limits
        if len(content) > 4000:
            return content[:4000] + f"\n\n... [truncated, {len(content)} total chars]"

        return content

    except PermissionError:
        return f"❌ Permission denied: {file_path}"
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"


async def write_file(file_path: str, content: str) -> str:
    """
    Write content to a file. Creates directories if needed.

    Args:
        file_path: Absolute path to the file.
        content: Text content to write.

    Returns:
        Success or error message.
    """
    return "❌ Write operations are disabled by policy."


async def delete_file(file_path: str) -> str:
    """
    Delete a file.

    Args:
        file_path: Absolute path to the file.

    Returns:
        Success or error message.
    """
    return "❌ Delete operations are disabled by policy."


async def list_files(directory: str) -> str:
    """
    List files and folders in a directory.

    Args:
        directory: Absolute path to the directory.

    Returns:
        Formatted listing or error message.
    """
    try:
        directory = _normalize_path(directory)
        if not _is_path_allowed(directory):
            return "❌ Access denied: directory is outside allowed paths."

        if not os.path.exists(directory):
            return f"❌ Directory not found: {directory}"

        if not os.path.isdir(directory):
            return f"❌ Not a directory: {directory}"

        entries = os.listdir(directory)
        if not entries:
            return f"📁 {directory} is empty."

        # Sort: directories first, then files
        dirs = []
        files = []
        for entry in sorted(entries):
            full_path = os.path.join(directory, entry)
            if os.path.isdir(full_path):
                dirs.append(f"📁 {entry}/")
            else:
                try:
                    size = os.path.getsize(full_path)
                    files.append(f"📄 {entry} ({_format_size(size)})")
                except OSError:
                    files.append(f"📄 {entry}")

        result_lines = [f"📂 **{directory}**\n"]
        result_lines.extend(dirs)
        result_lines.extend(files)
        result = "\n".join(result_lines)

        # Truncate if too many entries
        if len(result) > 3500:
            count_shown = result[:3500].count("\n")
            result = result[:3500] + f"\n\n... [{len(entries)} total entries, showing ~{count_shown}]"

        return result

    except PermissionError:
        return f"❌ Permission denied: {directory}"
    except Exception as e:
        return f"❌ Error listing directory: {str(e)}"


async def search_files(query: str, directory: str = "C:\\") -> str:
    """
    Search for files by name pattern.

    Args:
        query: Search pattern (supports wildcards).
        directory: Directory to search in.

    Returns:
        List of matching files or error message.
    """
    try:
        directory = _normalize_path(directory)
        if not _is_path_allowed(directory):
            return "❌ Access denied: directory is outside allowed paths."

        if not os.path.isdir(directory):
            return f"❌ Directory not found: {directory}"

        # Use glob for pattern matching
        pattern = os.path.join(directory, "**", f"*{query}*")
        matches = []
        for match in glob.iglob(pattern, recursive=True):
            matches.append(match)
            if len(matches) >= 50:  # Limit results
                break

        if not matches:
            return f"🔍 No files matching '{query}' found in {directory}"

        result = f"🔍 **Search results for '{query}':**\n\n"
        for m in matches:
            if os.path.isdir(m):
                result += f"📁 {m}\n"
            else:
                try:
                    size = os.path.getsize(m)
                    result += f"📄 {m} ({_format_size(size)})\n"
                except OSError:
                    result += f"📄 {m}\n"

        if len(matches) >= 50:
            result += "\n⚠️ Results limited to 50 matches."

        return result

    except Exception as e:
        return f"❌ Error searching: {str(e)}"


def get_file_path(file_path: str) -> Optional[str]:
    """
    Validate and return the absolute path if the file exists.

    Used to send files via Telegram.

    Returns:
        Absolute path if valid, None otherwise.
    """
    file_path = _normalize_path(file_path)
    if _is_path_allowed(file_path) and os.path.isfile(file_path):
        return file_path
    return None


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    else:
        return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"


def _normalize_path(path_value: str) -> str:
    return os.path.normcase(os.path.abspath(os.path.expandvars(os.path.expanduser(path_value))))


def _is_path_allowed(path_value: str) -> bool:
    allowed = config.ALLOWED_FILE_DIRS
    if not allowed:
        return False
    try:
        return any(os.path.commonpath([path_value, base]) == base for base in allowed)
    except ValueError:
        return False
