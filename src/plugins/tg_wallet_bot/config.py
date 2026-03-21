"""
Telegram Plugin Config  [WALLET BOT only — OpenClaw agent has its own config]
======================
All configuration loaded from environment variables.
No defaults for secrets — missing values raise at startup.

TWO BOT TOKENS IN .env:
    TELEGRAM_BOT_TOKEN         → OpenClaw agent bot (managed by OpenClaw, not this code)
    TELEGRAM_WALLET_BOT_TOKEN  → Wallet bot (poller.py / interceptor.py use THIS one)

get_bot_token() prefers WALLET token. Falls back to BOT token for backward compat.
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
    # Prefer the wallet-specific token if set, so you can have both in .env:
    #   TELEGRAM_WALLET_BOT_TOKEN = token for @YourWalletBot  (this poller)
    #   TELEGRAM_BOT_TOKEN        = token for @YourAIBot      (OpenClaw — its own config)
    # Falls back to TELEGRAM_BOT_TOKEN for backward compatibility.
    wallet_token = os.getenv("TELEGRAM_WALLET_BOT_TOKEN", "").strip()
    if wallet_token:
        return wallet_token
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
