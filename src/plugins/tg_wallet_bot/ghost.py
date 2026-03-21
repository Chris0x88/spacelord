"""
Ghost Tunnel — Secure Key Input Endpoint (Phase 4)
===================================================
Receives sensitive values from the Telegram Mini App and writes them
to the .env file WITHOUT ever logging the actual value.

Security model:
  - Only TELEGRAM_BOT_TOKEN holders can sign valid initData
  - initData is validated via HMAC-SHA256 before any write
  - Field names are hardcoded (no dynamic injection from user input)
  - Values are never written to logs or response bodies
  - .env writes are atomic (temp file + rename)
  - Rate limited: max 3 writes per minute per Telegram user ID

Endpoint: POST /ghost
  Body: {field: str, value: str, init_data: str}
  Response: {status: "saved", field: str}

GET /mini-app/secure-input  →  served by interceptor.py
"""

import hashlib
import hmac
import logging
import os
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("pacman.telegram.ghost")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Hardcoded whitelist — DO NOT make this dynamic
ALLOWED_FIELDS = frozenset({"PRIVATE_KEY", "ROBOT_PRIVATE_KEY", "PACMAN_API_SECRET"})

# Rate limiting: max writes per window per user
RATE_LIMIT_MAX = 3
RATE_LIMIT_WINDOW = 60  # seconds

# In-memory rate limit store: {user_id: [timestamp, ...]}
_rate_store: Dict[int, list] = {}

# Path to repo root .env
_ENV_PATH = Path(__file__).resolve().parent.parent.parent.parent / ".env"


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class GhostRequest(BaseModel):
    field: str
    value: str
    init_data: str  # Telegram WebApp initData string


# ---------------------------------------------------------------------------
# Public endpoint handler
# ---------------------------------------------------------------------------

async def handle_ghost(request: Request, body: GhostRequest, bot_token: str) -> JSONResponse:
    """
    POST /ghost — receive a sensitive field value from the Mini App.

    Steps:
      1. Validate field name against whitelist
      2. Validate Telegram initData HMAC
      3. Check rate limit for this user
      4. Write field to .env atomically
      5. Return success (field name only — never echo the value)
    """
    field = body.field.strip()
    value = body.value  # Do NOT strip — keys may be exact
    init_data = body.init_data

    # 1. Field whitelist check
    if field not in ALLOWED_FIELDS:
        logger.warning(f"[Ghost] Rejected write to non-whitelisted field: {field!r}")
        raise HTTPException(status_code=400, detail="Field not permitted")

    # 2. Validate Telegram initData
    user_id, valid = _validate_init_data(init_data, bot_token)
    if not valid:
        logger.warning("[Ghost] initData validation failed — possible forgery")
        raise HTTPException(status_code=403, detail="Invalid Telegram authentication")

    # 3. Rate limit per user
    if not _check_rate_limit(user_id):
        logger.warning(f"[Ghost] Rate limit exceeded for user {user_id}")
        raise HTTPException(status_code=429, detail="Too many requests — wait a moment")

    # 4. Validate value is non-empty
    if not value:
        raise HTTPException(status_code=400, detail="Value must not be empty")

    # 5. Atomic .env write
    try:
        _write_env_field(field, value)
    except Exception as exc:
        logger.error(f"[Ghost] Failed to write {field} to .env: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save — check server logs")

    # Log field name only — NEVER the value
    logger.info(f"[Ghost] Field {field!r} updated successfully by user {user_id}")

    return JSONResponse({"status": "saved", "field": field})


# ---------------------------------------------------------------------------
# Telegram initData validation
# ---------------------------------------------------------------------------

def _validate_init_data(init_data: str, bot_token: str) -> Tuple[int, bool]:
    """
    Validate Telegram Mini App initData using HMAC-SHA256.

    Per Telegram docs:
      secret_key = HMAC-SHA256(key="WebAppData", msg=bot_token)
      data_check_string = sorted key=value pairs (excl. hash) joined by \\n
      expected_hash = HMAC-SHA256(key=secret_key, msg=data_check_string).hex()

    Returns (user_id, is_valid).
    """
    if not init_data:
        return 0, False

    try:
        params = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return 0, False

    received_hash = params.pop("hash", None)
    if not received_hash:
        return 0, False

    # Build data_check_string: sorted key=value pairs joined by \n
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )

    # Derive the secret key
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()

    # Compute expected hash
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        return 0, False

    # Extract user_id from the "user" JSON field
    user_id = 0
    try:
        import json
        user_json = params.get("user", "{}")
        user_data = json.loads(user_json)
        user_id = int(user_data.get("id", 0))
    except Exception:
        pass

    return user_id, True


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def _check_rate_limit(user_id: int) -> bool:
    """
    Return True if the user is within the rate limit window.
    Slides the window on each call.
    """
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW

    timestamps = _rate_store.get(user_id, [])
    # Prune old timestamps
    timestamps = [t for t in timestamps if t > window_start]

    if len(timestamps) >= RATE_LIMIT_MAX:
        return False

    timestamps.append(now)
    _rate_store[user_id] = timestamps
    return True


# ---------------------------------------------------------------------------
# Atomic .env writer
# ---------------------------------------------------------------------------

def _write_env_field(field: str, value: str) -> None:
    """
    Update a single field in the .env file without disturbing other values.
    Uses a temp file + rename for atomicity.

    If the field already exists, its line is updated in place.
    If it does not exist, it is appended.
    """
    env_path = _ENV_PATH

    # Read existing content (or start fresh)
    existing_lines: list = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    new_line = f"{field}={value}\n"
    found = False
    new_lines = []

    for line in existing_lines:
        stripped = line.strip()
        # Match "FIELD=..." or "# FIELD=..."
        if stripped.startswith(f"{field}=") or stripped == f"{field}":
            new_lines.append(new_line)
            found = True
        else:
            new_lines.append(line)

    if not found:
        # Ensure file ends with newline before appending
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(new_line)

    # Atomic write: write to sibling temp file, then rename
    env_dir = env_path.parent
    fd, tmp_path = tempfile.mkstemp(dir=env_dir, prefix=".env.tmp.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        os.replace(tmp_path, env_path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# WebApp button builder
# ---------------------------------------------------------------------------

def make_webapp_button(base_url: str, field: str = "PRIVATE_KEY") -> dict:
    """
    Return a Telegram InlineKeyboardMarkup with a single WebApp button
    that opens the secure input Mini App.

    Args:
        base_url: Public HTTPS URL of the Telegram interceptor server.
        field: Which field to pre-select in the Mini App.

    Example:
        {"inline_keyboard": [[{"text": "...", "web_app": {"url": "..."}}]]}
    """
    url = f"{base_url.rstrip('/')}/mini-app/secure-input?field={field}"
    return {
        "inline_keyboard": [
            [{"text": "\U0001f510 Enter Key Securely", "web_app": {"url": url}}]
        ]
    }
