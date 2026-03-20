"""
Telegram Long-Polling Runner
=============================
Zero external dependencies beyond httpx (already installed).
No ngrok, no tunnel, no public URL needed.

Polls Telegram's getUpdates API with a 30-second long-poll timeout,
so updates arrive near-instantly without busy-waiting.

Uses the SAME router + formatters as the webhook interceptor.

Start with:
    python -m src.plugins.telegram.poller

Or via launch.sh:
    ./launch.sh telegram-start
"""

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# ---------------------------------------------------------------------------
# Bootstrap: load .env before anything else
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _REPO_ROOT / ".env"

if _ENV_FILE.exists():
    with open(_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value

from src.plugins.telegram import config as tg_config
from src.plugins.telegram import formatters
from src.plugins.telegram.router import InboundRouter

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pacman.telegram")

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
_bot_token: str = ""
_allowed_users: set = set()
_router: Optional[InboundRouter] = None
_http: Optional[httpx.AsyncClient] = None
_shutdown = False


# ---------------------------------------------------------------------------
# Telegram Bot API helpers
# ---------------------------------------------------------------------------

async def _send(
    chat_id: int,
    text: str,
    reply_markup: Optional[Dict] = None,
    parse_mode: str = "HTML",
) -> None:
    """Send a message via the Telegram Bot API."""
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    url = f"https://api.telegram.org/bot{_bot_token}/sendMessage"
    try:
        resp = await _http.post(url, json=payload)
        if resp.status_code != 200:
            logger.warning(f"sendMessage failed: {resp.status_code} {resp.text[:200]}")
    except Exception as exc:
        logger.error(f"sendMessage error: {exc}")


async def _answer_callback(callback_query_id: str, text: str = "") -> None:
    """Acknowledge a callback query (clears Telegram's loading spinner)."""
    url = f"https://api.telegram.org/bot{_bot_token}/answerCallbackQuery"
    payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    try:
        await _http.post(url, json=payload)
    except Exception as exc:
        logger.error(f"answerCallbackQuery error: {exc}")


async def _delete_webhook() -> None:
    """Remove any existing webhook so getUpdates works."""
    url = f"https://api.telegram.org/bot{_bot_token}/deleteWebhook"
    try:
        resp = await _http.post(url)
        data = resp.json()
        if data.get("ok"):
            logger.info("Webhook cleared — polling mode active")
        else:
            logger.warning(f"deleteWebhook response: {data}")
    except Exception as exc:
        logger.error(f"deleteWebhook error: {exc}")


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

def _is_authorized(user_id: int) -> bool:
    if not _allowed_users:
        return True
    return user_id in _allowed_users


# ---------------------------------------------------------------------------
# Dispatch — identical logic to interceptor.py
# ---------------------------------------------------------------------------

async def _dispatch(update: Dict[str, Any]) -> None:
    """Parse a Telegram Update dict and route to the right handler."""

    # --- Message (slash command or free text) ---
    if "message" in update:
        msg = update["message"]
        user = msg.get("from", {})
        user_id = user.get("id", 0)
        chat_id = msg.get("chat", {}).get("id", 0)
        text = msg.get("text", "").strip()

        if not _is_authorized(user_id):
            await _send(chat_id, formatters.format_unauthorized(), reply_markup=None)
            return

        # web_app_data — sent by Mini App
        if "web_app_data" in msg:
            wad = msg["web_app_data"].get("data", "")
            response = _router.handle_web_app_data(wad, user_id)
            await _send(
                chat_id,
                response["text"],
                reply_markup=response.get("reply_markup"),
                parse_mode=response.get("parse_mode", "HTML"),
            )
            return

        if not text:
            return

        response = _router.handle_message(text, user_id)
        await _send(
            chat_id,
            response["text"],
            reply_markup=response.get("reply_markup"),
            parse_mode=response.get("parse_mode", "HTML"),
        )

    # --- Callback query (inline button press) ---
    elif "callback_query" in update:
        cq = update["callback_query"]
        user_id = cq.get("from", {}).get("id", 0)
        chat_id = cq.get("message", {}).get("chat", {}).get("id", 0)
        callback_data = cq.get("data", "")
        callback_query_id = cq.get("id", "")

        if not _is_authorized(user_id):
            await _answer_callback(callback_query_id, text="Access denied.")
            return

        # confirm_swap:* — execute swap in thread pool
        if callback_data.startswith("confirm_swap:"):
            await _answer_callback(callback_query_id)
            await _send(
                chat_id,
                "\u23f3 <b>Executing swap\u2026</b>\n\n<i>Submitting to Hedera. Please wait.</i>",
                reply_markup=None,
            )
            try:
                response = await asyncio.to_thread(
                    _router.execute_swap_callback, callback_data
                )
            except Exception as exc:
                logger.error(f"execute_swap_callback raised: {exc}", exc_info=True)
                response = {
                    "text": formatters.format_swap_error(f"Unexpected error: {exc}"),
                    "reply_markup": formatters.format_buttons(),
                    "parse_mode": "HTML",
                }
            await _send(
                chat_id,
                response["text"],
                reply_markup=response.get("reply_markup"),
                parse_mode=response.get("parse_mode", "HTML"),
            )
            return

        # confirm_send:* — execute send in thread pool
        if callback_data.startswith("confirm_send:"):
            await _answer_callback(callback_query_id)
            await _send(
                chat_id,
                "\u23f3 <b>Sending\u2026</b>\n\n<i>Submitting transfer to Hedera. Please wait.</i>",
                reply_markup=None,
            )
            try:
                response = await asyncio.to_thread(
                    _router.execute_send_callback, callback_data
                )
            except Exception as exc:
                logger.error(f"execute_send_callback raised: {exc}", exc_info=True)
                response = {
                    "text": formatters.format_send_error(f"Unexpected error: {exc}"),
                    "reply_markup": formatters.format_buttons(),
                    "parse_mode": "HTML",
                }
            await _send(
                chat_id,
                response["text"],
                reply_markup=response.get("reply_markup"),
                parse_mode=response.get("parse_mode", "HTML"),
            )
            return

        # All other callbacks — fast lane
        response = _router.handle_callback(callback_data, user_id)
        await _answer_callback(callback_query_id)
        await _send(
            chat_id,
            response["text"],
            reply_markup=response.get("reply_markup"),
            parse_mode=response.get("parse_mode", "HTML"),
        )


# ---------------------------------------------------------------------------
# Long-polling loop
# ---------------------------------------------------------------------------

async def _poll_loop() -> None:
    """
    Long-poll Telegram's getUpdates endpoint.

    timeout=30 means Telegram holds the connection open for up to 30 seconds
    before returning an empty result. When an update arrives, it returns
    immediately. This gives near-instant response with minimal bandwidth.
    """
    global _shutdown
    offset = 0
    base_url = f"https://api.telegram.org/bot{_bot_token}/getUpdates"
    backoff = 1  # seconds, for error recovery

    while not _shutdown:
        params: Dict[str, Any] = {
            "timeout": 30,
            "allowed_updates": ["message", "callback_query"],
        }
        if offset:
            params["offset"] = offset

        try:
            resp = await _http.get(base_url, params=params, timeout=40)
            data = resp.json()

            if not data.get("ok"):
                logger.error(f"getUpdates error: {data}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
                continue

            backoff = 1  # reset on success
            updates: List[Dict] = data.get("result", [])

            for update in updates:
                update_id = update.get("update_id", 0)
                offset = update_id + 1  # Acknowledge this update

                try:
                    await _dispatch(update)
                except Exception as exc:
                    logger.error(f"Dispatch error: {exc}", exc_info=True)

        except httpx.ReadTimeout:
            # Normal — 30-second long-poll expired with no updates
            continue
        except httpx.ConnectError:
            logger.warning(f"Connection error — retrying in {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
        except Exception as exc:
            logger.error(f"Poll error: {exc}", exc_info=True)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    global _bot_token, _allowed_users, _router, _http, _shutdown

    _bot_token = tg_config.get_bot_token()
    _allowed_users = tg_config.get_allowed_users()

    logger.info("Initialising PacmanController...")
    from src.controller import PacmanController
    controller = PacmanController()
    _router = InboundRouter(controller)

    _http = httpx.AsyncClient(timeout=40)

    # Clear any stale webhook so getUpdates works
    await _delete_webhook()

    # Verify bot identity
    try:
        resp = await _http.get(f"https://api.telegram.org/bot{_bot_token}/getMe")
        me = resp.json().get("result", {})
        bot_name = me.get("username", "unknown")
        logger.info(f"Bot: @{bot_name}")
    except Exception as exc:
        logger.error(f"getMe failed: {exc}")

    logger.info(
        f"Polling started. Allowed users: "
        f"{'(all)' if not _allowed_users else _allowed_users}"
    )
    logger.info("Press Ctrl+C to stop.")

    # Handle graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_shutdown)

    try:
        await _poll_loop()
    finally:
        await _http.aclose()
        logger.info("Telegram poller stopped.")


def _handle_shutdown() -> None:
    global _shutdown
    _shutdown = True
    logger.info("Shutdown signal received...")


if __name__ == "__main__":
    asyncio.run(main())
