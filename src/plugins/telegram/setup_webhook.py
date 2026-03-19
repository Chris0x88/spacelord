#!/usr/bin/env python3
"""
Telegram Webhook Setup Utility
==============================

Register, remove, or inspect the Telegram Bot API webhook.

Usage:
    python -m src.plugins.telegram.setup_webhook set      # Register webhook
    python -m src.plugins.telegram.setup_webhook delete   # Remove webhook
    python -m src.plugins.telegram.setup_webhook info     # Show current webhook
"""

import os
import sys
import json
import httpx
from pathlib import Path

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")
except ImportError:
    pass

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _check_token():
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set in environment or .env")
        sys.exit(1)


def cmd_set():
    """Register the webhook with Telegram."""
    _check_token()
    if not WEBHOOK_URL:
        print("Error: TELEGRAM_WEBHOOK_URL not set in environment or .env")
        sys.exit(1)

    url = f"{WEBHOOK_URL}/webhook"
    params = {
        "url": url,
        "allowed_updates": json.dumps(["message", "callback_query", "web_app_data"]),
    }
    if WEBHOOK_SECRET:
        params["secret_token"] = WEBHOOK_SECRET

    resp = httpx.post(f"{API_BASE}/setWebhook", data=params, timeout=15)
    data = resp.json()

    if data.get("ok"):
        print(f"Webhook set: {url}")
        if WEBHOOK_SECRET:
            print(f"Secret token: configured")
    else:
        print(f"Failed: {data.get('description', 'Unknown error')}")
        sys.exit(1)


def cmd_delete():
    """Remove the webhook."""
    _check_token()
    resp = httpx.post(f"{API_BASE}/deleteWebhook", timeout=15)
    data = resp.json()

    if data.get("ok"):
        print("Webhook removed.")
    else:
        print(f"Failed: {data.get('description', 'Unknown error')}")
        sys.exit(1)


def cmd_info():
    """Show current webhook configuration."""
    _check_token()
    resp = httpx.get(f"{API_BASE}/getWebhookInfo", timeout=15)
    data = resp.json()

    if data.get("ok"):
        info = data["result"]
        print(f"URL:              {info.get('url') or '(not set)'}")
        print(f"Pending updates:  {info.get('pending_update_count', 0)}")
        print(f"Last error:       {info.get('last_error_message', '(none)')}")
        print(f"Last error date:  {info.get('last_error_date', '(none)')}")
        print(f"Max connections:  {info.get('max_connections', 40)}")
        print(f"Has secret:       {bool(info.get('has_custom_certificate', False))}")
    else:
        print(f"Failed: {data.get('description', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    action = sys.argv[1].lower()
    actions = {"set": cmd_set, "delete": cmd_delete, "info": cmd_info}

    if action not in actions:
        print(f"Unknown action: {action}")
        print(f"Valid: {', '.join(actions.keys())}")
        sys.exit(1)

    actions[action]()
