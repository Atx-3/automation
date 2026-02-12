"""
config.py — Central configuration for the AI Assistant.

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


# ── Telegram ──────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = _require_env("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALLOWED_USER_ID: int = int(_require_env("TELEGRAM_ALLOWED_USER_ID"))

# ── Ollama ────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

# ── Rate Limiting ─────────────────────────────────────────────────────
RATE_LIMIT_RPM: int = int(os.getenv("RATE_LIMIT_RPM", "30"))

# ── Logging ───────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE: str = os.getenv("LOG_FILE", "assistant.log")

# ── FastAPI ───────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR: str = os.path.join(BASE_DIR, "screenshots")

# Ensure screenshot directory exists
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
