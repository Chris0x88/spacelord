"""
Telegram Interceptor — FastAPI Webhook Server
=============================================
Receives Telegram bot updates via HTTPS webhook and routes them
to the fast lane (PacmanController) or the AI lane (Phase 2+).

Start with:
    uvicorn src.plugins.telegram.interceptor:app --host 0.0.0.0 --port 8443

Or via launch.sh:
    ./launch.sh telegram-start

Environment variables (see config.py):
    TELEGRAM_BOT_TOKEN        required
    TELEGRAM_WEBHOOK_URL      required  (your public HTTPS URL)
    TELEGRAM_WEBHOOK_SECRET   optional  (recommended for production)
    TELEGRAM_ALLOWED_USERS    optional  (comma-separated numeric IDs)
    TELEGRAM_PORT             optional  (default: 8443)

Architecture:
    POST /webhook
        → validate secret header
        → parse Telegram Update
        → check user authorization
        → InboundRouter.handle_message() or handle_callback()
        → Bot.send_message() with HTML + inline keyboard
"""

import asyncio
import hashlib
import hmac
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from src.plugins.telegram import config as tg_config
from src.plugins.telegram import formatters
from src.plugins.telegram.ghost import GhostRequest, handle_ghost, make_webapp_button
from src.plugins.telegram.router import InboundRouter

logger = logging.getLogger("pacman.telegram")

# ---------------------------------------------------------------------------
# Globals — initialised once at startup
# ---------------------------------------------------------------------------

_controller = None   # PacmanController
_router: Optional[InboundRouter] = None
_bot_token: str = ""
_webhook_secret: str = ""
_allowed_users: set = set()


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialise controller + bot once at startup."""
    global _controller, _router, _bot_token, _webhook_secret, _allowed_users

    logger.info("[Telegram] Interceptor starting up...")

    _bot_token = tg_config.get_bot_token()
    _webhook_secret = tg_config.get_webhook_secret()
    _allowed_users = tg_config.get_allowed_users()

    # Lazy import so the module can be imported without Hedera deps installed
    from src.controller import PacmanController
    _controller = PacmanController()
    _router = InboundRouter(_controller)

    logger.info(
        f"[Telegram] Ready. Allowed users: "
        f"{'(all)' if not _allowed_users else _allowed_users}"
    )

    yield  # Server is running

    logger.info("[Telegram] Shutting down interceptor.")


app = FastAPI(title="Pacman Telegram Interceptor", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@app.post("/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
) -> Response:
    """
    Receive a Telegram Update.

    Telegram sends this header when a webhook secret is set:
        X-Telegram-Bot-Api-Secret-Token: <secret>
    """
    # 1. Validate secret token (if configured)
    if _webhook_secret:
        if not hmac.compare_digest(
            x_telegram_bot_api_secret_token, _webhook_secret
        ):
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    # 2. Parse body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 3. Dispatch (async — don't block Telegram's 5-second timeout)
    try:
        await _dispatch(body)
    except Exception as exc:
        logger.error(f"[Telegram] Dispatch error: {exc}", exc_info=True)
        # Always return 200 so Telegram doesn't retry endlessly
    return Response(status_code=200)


@app.get("/health")
async def health() -> Dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "service": "pacman-telegram-interceptor"}


# ---------------------------------------------------------------------------
# Ghost Tunnel — Phase 4
# ---------------------------------------------------------------------------

_MINI_APP_HTML = Path(__file__).resolve().parent / "mini_app" / "secure_input.html"


@app.post("/ghost")
async def ghost(request: Request, body: GhostRequest) -> JSONResponse:
    """
    Receive a sensitive field value from the Telegram Mini App.
    Validates initData, rate-limits by user, writes to .env atomically.
    The actual value is NEVER logged or echoed back.
    """
    return await handle_ghost(request, body, _bot_token)


@app.get("/mini-app/secure-input")
async def mini_app_secure_input() -> FileResponse:
    """Serve the Ghost Tunnel Mini App HTML page."""
    if not _MINI_APP_HTML.exists():
        raise HTTPException(status_code=404, detail="Mini App not found")
    return FileResponse(_MINI_APP_HTML, media_type="text/html")


def build_webapp_button(field: str = "PRIVATE_KEY") -> Optional[Dict]:
    """
    Return a Telegram InlineKeyboardMarkup with a WebApp button for secure key input.
    Returns None if TELEGRAM_WEBHOOK_URL is not configured.

    Usage in a sendMessage payload:
        {"reply_markup": build_webapp_button("PRIVATE_KEY")}
    """
    try:
        base_url = tg_config.get_webhook_url()
        # Derive server base URL from webhook URL (strip /webhook path if present)
        if base_url.endswith("/webhook"):
            base_url = base_url[: -len("/webhook")]
        return make_webapp_button(base_url, field)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Dispatch logic
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

        # web_app_data — sent by Mini App via Telegram.WebApp.sendData()
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
            return  # Ignore non-text messages (photos, stickers, etc.)

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

        # confirm_swap:* — execute asynchronously so we don't block Telegram's
        # 5-second webhook timeout and so the user sees an immediate response.
        if callback_data.startswith("confirm_swap:"):
            await _execute_swap_async(callback_data, chat_id, callback_query_id)
            return

        # confirm_send:* — same async pattern for blocking transfer RPC calls
        if callback_data.startswith("confirm_send:"):
            await _execute_send_async(callback_data, chat_id, callback_query_id)
            return

        response = _router.handle_callback(callback_data, user_id)
        # Acknowledge the button press first (removes loading spinner)
        await _answer_callback(callback_query_id)
        await _send(
            chat_id,
            response["text"],
            reply_markup=response.get("reply_markup"),
            parse_mode=response.get("parse_mode", "HTML"),
        )

    else:
        # Edited messages, channel posts, etc. — silently ignore
        pass


# ---------------------------------------------------------------------------
# Async swap execution (Phase 2)
# ---------------------------------------------------------------------------

async def _execute_swap_async(
    callback_data: str,
    chat_id: int,
    callback_query_id: str,
) -> None:
    """
    Handle a confirm_swap:* callback without blocking Telegram's webhook timeout.

    Flow:
      1. ACK the button press immediately (clears Telegram's loading spinner).
      2. Send "⏳ Executing…" so the user knows work is in progress.
      3. Run the blocking controller.swap() call in a thread pool.
      4. Send the receipt (or error message) when done.
    """
    # 1. Acknowledge immediately
    await _answer_callback(callback_query_id)

    # 2. Notify user swap is in progress
    await _send(
        chat_id,
        "\u23f3 <b>Executing swap\u2026</b>\n\n<i>Submitting to Hedera. Please wait.</i>",
        reply_markup=None,
    )

    # 3. Run blocking swap in a thread pool
    try:
        response = await asyncio.to_thread(
            _router.execute_swap_callback, callback_data
        )
    except Exception as exc:
        logger.error(f"[Telegram] execute_swap_callback raised: {exc}", exc_info=True)
        response = {
            "text": formatters.format_swap_error(
                f"Unexpected error: {exc}"
            ),
            "reply_markup": formatters.format_buttons(),
            "parse_mode": "HTML",
        }

    # 4. Send receipt or error
    await _send(
        chat_id,
        response["text"],
        reply_markup=response.get("reply_markup"),
        parse_mode=response.get("parse_mode", "HTML"),
    )


# ---------------------------------------------------------------------------
# Async send execution (Phase 3)
# ---------------------------------------------------------------------------

async def _execute_send_async(
    callback_data: str,
    chat_id: int,
    callback_query_id: str,
) -> None:
    """
    Handle a confirm_send:* callback without blocking Telegram's webhook timeout.

    Flow:
      1. ACK the button press immediately.
      2. Send "⏳ Sending…" message.
      3. Run the blocking controller.transfer() call in a thread pool.
      4. Send the receipt (or error message) when done.
    """
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
        logger.error(f"[Telegram] execute_send_callback raised: {exc}", exc_info=True)
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


# ---------------------------------------------------------------------------
# Telegram Bot API calls (thin HTTP wrappers — no full framework needed)
# ---------------------------------------------------------------------------

async def _send(
    chat_id: int,
    text: str,
    reply_markup: Optional[Dict] = None,
    parse_mode: str = "HTML",
) -> None:
    """Send a message via the Telegram Bot API."""
    import httpx

    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    url = f"https://api.telegram.org/bot{_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            logger.warning(
                f"[Telegram] sendMessage failed: {resp.status_code} {resp.text[:200]}"
            )


async def _answer_callback(callback_query_id: str, text: str = "") -> None:
    """Acknowledge a callback query (clears Telegram's loading spinner)."""
    import httpx

    url = f"https://api.telegram.org/bot{_bot_token}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(url, json=payload)


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

def _is_authorized(user_id: int) -> bool:
    """Return True if user is allowed (or if no allowlist is configured)."""
    if not _allowed_users:
        return True
    return user_id in _allowed_users


# ---------------------------------------------------------------------------
# CLI entry point for direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = tg_config.get_port()
    uvicorn.run("src.plugins.telegram.interceptor:app", host="0.0.0.0", port=port, reload=False)
