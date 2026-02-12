"""
security.py — Authentication and rate limiting for the AI Assistant.

Handles:
- Telegram user ID verification (only the owner can use the bot)
- Sliding-window rate limiting to prevent abuse
"""

import time
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


def verify_user(user_id: int, allowed_user_id: int) -> bool:
    """
    Verify that the Telegram user is the authorized owner.

    Args:
        user_id: The incoming user's Telegram ID.
        allowed_user_id: The configured owner's Telegram ID.

    Returns:
        True if the user is authorized.
    """
    return user_id == allowed_user_id


def sanitize_input(text: str, max_length: int = 4096) -> str:
    """
    Basic input sanitization.

    Truncates excessively long messages to prevent abuse.

    Args:
        text: Raw input text.
        max_length: Maximum allowed characters.

    Returns:
        Sanitized string.
    """
    if not text:
        return ""
    return text.strip()[:max_length]
