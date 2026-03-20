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
import time
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

# Dedup guard: track recently processed confirm callback_query_ids
# Maps callback_query_id → timestamp. Prevents double-tap and stale replay.
_recent_confirm_ids: Dict[str, float] = {}
_CONFIRM_DEDUP_TTL = 30.0  # seconds


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
        "chat_id": str(chat_id),
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    url = f"https://api.telegram.org/bot{_bot_token}/sendMessage"
    try:
        resp = await _http.post(url, data=payload)
        if resp.status_code != 200:
            logger.warning(f"sendMessage failed: {resp.status_code} {resp.text[:200]}")
        else:
            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"sendMessage not ok: {data.get('description', '')[:200]}")
    except Exception as exc:
        logger.error(f"sendMessage error: {exc}")


async def _answer_callback(callback_query_id: str, text: str = "") -> None:
    """Acknowledge a callback query (clears Telegram's loading spinner)."""
    url = f"https://api.telegram.org/bot{_bot_token}/answerCallbackQuery"
    payload: Dict[str, str] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    try:
        await _http.post(url, data=payload)
    except Exception as exc:
        logger.error(f"answerCallbackQuery error: {exc}")


async def _edit(
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: Optional[Dict] = None,
    parse_mode: str = "HTML",
) -> bool:
    """Edit an existing message. Returns True on success, False on failure."""
    payload: Dict[str, Any] = {
        "chat_id": str(chat_id),
        "message_id": str(message_id),
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    else:
        # Explicitly remove keyboard when reply_markup is None
        payload["reply_markup"] = json.dumps({"inline_keyboard": []})

    url = f"https://api.telegram.org/bot{_bot_token}/editMessageText"
    try:
        resp = await _http.post(url, data=payload)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return True
            logger.warning(f"editMessageText not ok: {data.get('description', '')[:200]}")
        else:
            logger.warning(f"editMessageText failed: {resp.status_code} {resp.text[:200]}")
    except Exception as exc:
        logger.error(f"editMessageText error: {exc}")
    return False


async def _delete_webhook() -> None:
    """Remove any existing webhook so getUpdates works."""
    url = f"https://api.telegram.org/bot{_bot_token}/deleteWebhook"
    try:
        resp = await _http.post(url, data={})
        data = resp.json()
        if data.get("ok"):
            logger.info("Webhook cleared — polling mode active")
        else:
            logger.warning(f"deleteWebhook response: {data}")
    except Exception as exc:
        logger.error(f"deleteWebhook error: {exc}")


async def _register_commands() -> None:
    """Register bot commands with Telegram so they appear in the '/' menu."""
    commands = [
        {"command": "start",     "description": "Open wallet home screen"},
        {"command": "portfolio", "description": "View balances & USD values"},
        {"command": "swap",      "description": "Swap tokens (button-driven)"},
        {"command": "send",      "description": "Send tokens to whitelisted address"},
        {"command": "price",     "description": "Live token prices"},
        {"command": "gas",       "description": "Check HBAR gas reserve"},
        {"command": "history",   "description": "Recent transactions"},
        {"command": "robot",     "description": "BTC rebalancer status"},
        {"command": "tokens",    "description": "Supported tokens list"},
        {"command": "status",    "description": "System health check"},
        {"command": "setup",     "description": "Secure key setup (Mini App)"},
        {"command": "menu",      "description": "Show main menu"},
    ]
    url = f"https://api.telegram.org/bot{_bot_token}/setMyCommands"
    try:
        resp = await _http.post(url, json={"commands": commands})
        data = resp.json()
        if data.get("ok"):
            logger.info(f"Registered {len(commands)} bot commands with Telegram")
        else:
            logger.warning(f"setMyCommands response: {data}")
    except Exception as exc:
        logger.error(f"setMyCommands error: {exc}")


# ---------------------------------------------------------------------------
# Startup safety: drain stale updates
# ---------------------------------------------------------------------------

async def _drain_stale_updates() -> None:
    """
    Acknowledge (without processing) any updates that piled up while the bot
    was offline. This is CRITICAL for a trading bot — without this, a pending
    'confirm_swap' callback from a previous session can replay and fire a trade
    the user never intentionally triggered after restart.
    """
    url = f"https://api.telegram.org/bot{_bot_token}/getUpdates"
    try:
        resp = await _http.get(url, params={"timeout": 0, "offset": -1})
        data = resp.json()
        updates = data.get("result", [])
        if updates:
            last_id = max(u["update_id"] for u in updates)
            # Acknowledge all pending updates without dispatching them
            await _http.get(url, params={"timeout": 0, "offset": last_id + 1})
            logger.warning(
                f"[Safety] Drained {len(updates)} stale pending update(s) on startup "
                f"(last_id={last_id}). Any queued confirm_swap/confirm_send callbacks "
                "were discarded to prevent unintended trade replay."
            )
        else:
            logger.info("[Safety] No stale updates — clean startup.")
    except Exception as exc:
        logger.error(f"_drain_stale_updates failed: {exc}")


def _is_confirm_already_processed(callback_query_id: str) -> bool:
    """
    Dedup guard against double-taps. Returns True if this confirm callback
    was already processed within the last CONFIRM_DEDUP_TTL seconds.
    Cleans up expired entries on each call.
    """
    now = time.monotonic()
    # Prune expired entries
    expired = [k for k, ts in _recent_confirm_ids.items() if now - ts > _CONFIRM_DEDUP_TTL]
    for k in expired:
        del _recent_confirm_ids[k]
    if callback_query_id in _recent_confirm_ids:
        return True
    _recent_confirm_ids[callback_query_id] = now
    return False


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

        # Check for pending custom amount input first
        pending_response = _router.handle_pending_input(text, user_id)
        if pending_response:
            await _send(
                chat_id,
                pending_response["text"],
                reply_markup=pending_response.get("reply_markup"),
                parse_mode=pending_response.get("parse_mode", "HTML"),
            )
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
        message_id = cq.get("message", {}).get("message_id", 0)
        callback_data = cq.get("data", "")
        callback_query_id = cq.get("id", "")

        if not _is_authorized(user_id):
            await _answer_callback(callback_query_id, text="Access denied.")
            return

        # confirm_swap:* — dedup check, show loading, execute in thread pool
        if callback_data.startswith("confirm_swap:"):
            if _is_confirm_already_processed(callback_query_id):
                logger.warning(f"[Dedup] Duplicate confirm_swap ignored: {callback_query_id}")
                await _answer_callback(callback_query_id, text="Already processing…")
                return
            await _answer_callback(callback_query_id)
            await _edit(
                chat_id, message_id,
                "⏳ <b>Executing swap…</b>\n\n<i>Submitting to Hedera. Please wait.</i>",
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
            edited = await _edit(
                chat_id, message_id,
                response["text"],
                reply_markup=response.get("reply_markup"),
                parse_mode=response.get("parse_mode", "HTML"),
            )
            if not edited:
                await _send(
                    chat_id,
                    response["text"],
                    reply_markup=response.get("reply_markup"),
                    parse_mode=response.get("parse_mode", "HTML"),
                )
            return

        # confirm_send:* — same pattern with dedup
        if callback_data.startswith("confirm_send:"):
            if _is_confirm_already_processed(callback_query_id):
                logger.warning(f"[Dedup] Duplicate confirm_send ignored: {callback_query_id}")
                await _answer_callback(callback_query_id, text="Already processing…")
                return
            await _answer_callback(callback_query_id)
            await _edit(
                chat_id, message_id,
                "⏳ <b>Sending…</b>\n\n<i>Submitting transfer to Hedera. Please wait.</i>",
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
            edited = await _edit(
                chat_id, message_id,
                response["text"],
                reply_markup=response.get("reply_markup"),
                parse_mode=response.get("parse_mode", "HTML"),
            )
            if not edited:
                await _send(
                    chat_id,
                    response["text"],
                    reply_markup=response.get("reply_markup"),
                    parse_mode=response.get("parse_mode", "HTML"),
                )
            return

        # All other callbacks — fast lane.
        # Answer the callback FIRST so Telegram's button spinner clears immediately
        # (before potentially slow network calls for portfolio/prices/etc.)
        await _answer_callback(callback_query_id)
        response = _router.handle_callback(callback_data, user_id)
        edited = await _edit(
            chat_id, message_id,
            response["text"],
            reply_markup=response.get("reply_markup"),
            parse_mode=response.get("parse_mode", "HTML"),
        )
        if not edited:
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

    # SAFETY: drain any updates that accumulated while offline.
    # Must happen before _register_commands and the poll loop.
    await _drain_stale_updates()

    # Register bot commands so they appear in Telegram's "/" menu
    await _register_commands()

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
