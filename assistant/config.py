"""
config.py — Central configuration for Chapna AI Assistant.

Loads environment variables from .env and provides typed access
to all settings used across the application.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file from the same directory as this script
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_ENV_PATH)


def _require_env(key: str) -> str:
    """Get a required environment variable or exit with an error."""
    value = os.getenv(key)
    if not value:
        print(f"[FATAL] Missing required environment variable: {key}")
        print(f"        Please copy .env.example to .env and fill in your values.")
        sys.exit(1)
    return value


# ── Application Identity ─────────────────────────────────────────────
APP_NAME: str = "Chapna"
APP_VERSION: str = "2.0.0"

# ── Telegram ──────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = _require_env("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALLOWED_USER_IDS: list[int] = [
    int(uid.strip())
    for uid in _require_env("TELEGRAM_ALLOWED_USER_IDS").split(",")
    if uid.strip()
]

# ── Ollama ────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "120"))

# ── Rate Limiting ─────────────────────────────────────────────────────
RATE_LIMIT_RPM: int = int(os.getenv("RATE_LIMIT_RPM", "30"))

# ── Logging ───────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE: str = os.getenv("LOG_FILE", "chapna.log")

# ── FastAPI ───────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
API_TOKEN: str = os.getenv("API_TOKEN", "")  # Optional token for local API

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR: str = os.path.join(BASE_DIR, "screenshots")
SCRIPTS_DIR: str = os.path.join(BASE_DIR, "scripts")

# ── Email (Optional) ─────────────────────────────────────────────────
SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD: str = os.getenv("SENDER_PASSWORD", "")

# ── Whitelisted Applications ─────────────────────────────────────────
# Maps friendly name → executable path or command
WHITELISTED_APPS: dict[str, str] = {
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
    "spotify": os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
    "discord": os.path.expandvars(
        r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe"
    ),
    "telegram": os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
    "whatsapp": "explorer.exe shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
}

# ── Safe Scripts ──────────────────────────────────────────────────────
# Predefined scripts that can be run by name
SAFE_SCRIPTS: dict[str, str] = {
    # Example: "cleanup": os.path.join(SCRIPTS_DIR, "cleanup.bat"),
    # Example: "backup": os.path.join(SCRIPTS_DIR, "backup.ps1"),
}

# ── Ensure directories exist ─────────────────────────────────────────
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(SCRIPTS_DIR, exist_ok=True)
