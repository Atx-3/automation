"""
security.py — Authentication, rate limiting, and input validation for Chapna.

Handles:
- Telegram user ID verification (only allowed users can use the bot)
- Sliding-window rate limiting to prevent abuse
- Input sanitization and validation
- API token verification for local endpoints
"""

import time
import re
from collections import defaultdict
from typing import Optional


class RateLimiter:
    """
    Sliding-window rate limiter.

    Tracks request timestamps per user and rejects requests
    that exceed the configured rate.
    """

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        """
        Args:
            max_requests: Maximum allowed requests within the window.
            window_seconds: Time window in seconds.
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[int, list[float]] = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        """
        Check if the user is within the rate limit.

        Args:
            user_id: Identifier for the user (Telegram user ID).

        Returns:
            True if the request is allowed, False if rate-limited.
        """
        now = time.time()
        cutoff = now - self.window_seconds

        # Remove expired timestamps
        self._requests[user_id] = [
            ts for ts in self._requests[user_id] if ts > cutoff
        ]

        if len(self._requests[user_id]) >= self.max_requests:
            return False

        self._requests[user_id].append(now)
        return True

    def remaining(self, user_id: int) -> int:
        """Get the number of remaining requests for a user."""
        now = time.time()
        cutoff = now - self.window_seconds
        active = [ts for ts in self._requests.get(user_id, []) if ts > cutoff]
        return max(0, self.max_requests - len(active))


def verify_user(user_id: int, allowed_user_ids: list[int]) -> bool:
    """
    Verify that the Telegram user is in the allowed list.

    Args:
        user_id: The incoming user's Telegram ID.
        allowed_user_ids: List of authorized Telegram user IDs.

    Returns:
        True if the user is authorized.
    """
    return user_id in allowed_user_ids


def validate_api_token(provided_token: str, expected_token: str) -> bool:
    """
    Validate an API token for local endpoint access.

    Args:
        provided_token: Token sent in the request.
        expected_token: Expected token from config.

    Returns:
        True if token matches (or if no token is configured).
    """
    if not expected_token:
        return True  # No token required
    return provided_token == expected_token


def sanitize_input(text: str, max_length: int = 4096) -> str:
    """
    Basic input sanitization.

    Truncates excessively long messages and strips whitespace.

    Args:
        text: Raw input text.
        max_length: Maximum allowed characters.

    Returns:
        Sanitized string.
    """
    if not text:
        return ""
    return text.strip()[:max_length]


def extract_command_with_token(text: str, expected_token: str) -> tuple[bool, str]:
    if not expected_token:
        return True, text
    if not text:
        return False, ""
    direct_prefix = expected_token + " "
    if text.startswith(direct_prefix):
        return True, text[len(direct_prefix):].strip()
    pattern = r"^\s*token\s*[:=]\s*(\S+)\s+(.*)$"
    match = re.match(pattern, text, flags=re.IGNORECASE)
    if match and match.group(1) == expected_token:
        return True, match.group(2).strip()
    return False, ""


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate.

    Returns:
        True if email format is valid.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
