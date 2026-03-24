"""
Telegram Fast-Lane Command  [OPENCLAW AGENT — subprocess bridge]
===========================
Single CLI entry point for all Telegram button-driven operations.

Called by OpenClaw's Space Lord agent (TELEGRAM_BOT_TOKEN) when it receives
callback_data or slash commands from the AGENT Telegram chat.
Returns pre-formatted HTML + JSON button markup that OpenClaw passes
directly to Telegram's sendMessage API.

⚠️  This is the AGENT bot's fast-lane, invoked as:
        ./launch.sh tg portfolio
        ./launch.sh tg callback sf:0.0.456858
    It is NOT the wallet bot (poller.py), which calls the router directly.

Usage:
    ./launch.sh tg portfolio
    ./launch.sh tg swap
    ./launch.sh tg callback sf:0.0.456858
    ./launch.sh tg callback sa:0.0.456858:0.0.0:5

The --json flag is implicit — output is always structured for Telegram.
"""

import json
import sys
from pathlib import Path

from src.controller import SpaceLordController
from lib.tg_router import InboundRouter


def cmd_telegram(app, args):
    """
    Fast-lane Telegram command handler.

    Receives a Telegram action (slash command or callback_data) and
    returns a JSON response with {text, buttons, parse_mode} that
    OpenClaw can pass directly to Telegram's sendMessage API.
    """
    if not args:
        _output_help()
        return

    action = args[0].lower().lstrip("/")
    rest = " ".join(args[1:]) if len(args) > 1 else ""

    router = InboundRouter(app)

    # Route based on action type
    if action == "callback":
        # Raw callback_data from an inline button press
        if not rest:
            _output_error("Missing callback_data")
            return
        response = router.handle_callback(rest.strip(), user_id=0)
    elif action in ("start", "help", "menu"):
        response = router.handle_message(f"/{action}", user_id=0)
    elif action in ("portfolio", "balance"):
        response = router.handle_message("/portfolio", user_id=0)
    elif action == "swap":
        if rest:
            response = router.handle_message(f"swap {rest}", user_id=0)
        else:
            response = router.handle_callback("swap", user_id=0)
    elif action == "send":
        if rest:
            response = router.handle_message(f"send {rest}", user_id=0)
        else:
            response = router.handle_callback("send", user_id=0)
    elif action == "price":
        response = router.handle_message(f"/price {rest}".strip(), user_id=0)
    elif action in ("status", "health"):
        response = router.handle_message("/status", user_id=0)
    elif action == "gas":
        response = router.handle_message("/gas", user_id=0)
    elif action == "history":
        response = router.handle_message("/history", user_id=0)
    elif action == "tokens":
        response = router.handle_message("/tokens", user_id=0)
    elif action == "robot":
        response = router.handle_message("/robot", user_id=0)
    elif action == "orders":
        response = router.handle_message("/orders", user_id=0)
    elif action == "setup":
        response = router.handle_message(f"/setup {rest}".strip(), user_id=0)
    else:
        # Try as a generic message (natural language or unknown command)
        response = router.handle_message(rest if rest else action, user_id=0)

    _output_response(response)


def _output_response(response):
    """Print structured JSON for OpenClaw to parse and forward to Telegram."""
    output = {
        "text": response.get("text", ""),
        "parse_mode": response.get("parse_mode", "HTML"),
    }

    # Extract buttons from reply_markup
    markup = response.get("reply_markup")
    if markup and isinstance(markup, dict):
        buttons = markup.get("inline_keyboard")
        if buttons:
            output["buttons"] = buttons

    print(json.dumps(output, ensure_ascii=False))


def _output_error(msg):
    """Print an error response."""
    from lib.tg_format import format_error, format_buttons
    output = {
        "text": format_error(msg),
        "parse_mode": "HTML",
        "buttons": format_buttons()["inline_keyboard"],
    }
    print(json.dumps(output, ensure_ascii=False))


def _output_help():
    """Print usage help."""
    from lib.tg_format import format_welcome, format_buttons
    output = {
        "text": format_welcome(),
        "parse_mode": "HTML",
        "buttons": format_buttons()["inline_keyboard"],
    }
    print(json.dumps(output, ensure_ascii=False))
