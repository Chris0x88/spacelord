"""
Telegram Plugin Config
======================
All configuration loaded from environment variables.
No defaults for secrets — missing values raise at startup.
"""

import os
from typing import Set


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def get_bot_token() -> str:
    return _require("TELEGRAM_BOT_TOKEN")


def get_webhook_url() -> str:
    return _require("TELEGRAM_WEBHOOK_URL")


def get_webhook_secret() -> str:
    """Secret token used to validate Telegram webhook requests."""
    return _optional("TELEGRAM_WEBHOOK_SECRET")


def get_allowed_users() -> Set[int]:
    """
    Comma-separated Telegram numeric user IDs allowed to use the bot.
    Empty = no restriction (open to anyone who can message the bot).
    """
    raw = _optional("TELEGRAM_ALLOWED_USERS")
    if not raw:
        return set()
    result = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            result.add(int(part))
    return result


def get_port() -> int:
    raw = _optional("TELEGRAM_PORT", "8443")
    try:
        return int(raw)
    except ValueError:
        return 8443
