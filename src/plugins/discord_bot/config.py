"""
Discord Plugin Config
=====================
All configuration loaded from environment variables.
No defaults for secrets — missing values raise at startup.

Environment variables:
    DISCORD_BOT_TOKEN      → Bot token from Discord Developer Portal
    DISCORD_ALLOWED_USERS  → Comma-separated Discord user IDs (empty = open)
    DISCORD_GUILD_ID       → Optional: guild ID for instant slash command sync
"""

import os
from typing import Optional, Set


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def get_bot_token() -> str:
    return _require("DISCORD_BOT_TOKEN")


def get_allowed_users() -> Set[int]:
    """
    Comma-separated Discord numeric user IDs allowed to use the bot.
    Empty = no restriction (open to anyone in the server).
    """
    raw = _optional("DISCORD_ALLOWED_USERS")
    if not raw:
        return set()
    result = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            result.add(int(part))
    return result


def get_guild_id() -> Optional[int]:
    """
    Optional guild ID for instant slash command registration.
    Without this, global commands take up to 1 hour to propagate.
    """
    raw = _optional("DISCORD_GUILD_ID")
    if raw and raw.isdigit():
        return int(raw)
    return None
