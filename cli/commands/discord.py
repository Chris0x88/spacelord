"""
Discord Fast-Lane Command  [UNTESTED PLUGIN — OpenClaw agent subprocess bridge]
================================================================================
⚠️  UNTESTED: Mirrors cli/commands/telegram.py exactly but has not been
    exercised through a full OpenClaw agent session.

Single CLI entry point for all Discord button-driven operations.
Same router as Telegram, different output format (Discord markdown + buttons).

Called by OpenClaw's pacman agent when it receives interactions from Discord.
Returns pre-formatted Discord markdown + JSON button markup.

Usage:
    ./launch.sh dc portfolio
    ./launch.sh dc swap
    ./launch.sh dc callback sf:0.0.456858
"""

import json
import sys
from pathlib import Path

from src.controller import PacmanController
from lib.tg_router import InboundRouter
from lib.dc_format import convert_response


def cmd_discord(app, args):
    """
    Fast-lane Discord command handler.

    Receives a Discord action (slash command or callback_data) and
    returns a JSON response with {content, buttons} in Discord format.
    """
    if not args:
        _output_help()
        return

    action = args[0].lower().lstrip("/")
    rest = " ".join(args[1:]) if len(args) > 1 else ""

    router = InboundRouter(app)

    # Route based on action type (mirrors telegram.py exactly)
    if action == "callback":
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
        response = router.handle_message(rest if rest else action, user_id=0)

    _output_response(response)


def _output_response(response):
    """Print structured JSON in Discord format."""
    converted = convert_response(response)
    print(json.dumps(converted, ensure_ascii=False))


def _output_error(msg):
    """Print an error response."""
    from lib.tg_format import format_error, format_buttons
    response = {
        "text": format_error(msg),
        "reply_markup": format_buttons(),
        "parse_mode": "HTML",
    }
    converted = convert_response(response)
    print(json.dumps(converted, ensure_ascii=False))


def _output_help():
    """Print usage help."""
    from lib.tg_format import format_welcome, format_buttons
    response = {
        "text": format_welcome(),
        "reply_markup": format_buttons(),
        "parse_mode": "HTML",
    }
    converted = convert_response(response)
    print(json.dumps(converted, ensure_ascii=False))
