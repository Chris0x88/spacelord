#!/usr/bin/env python3
"""
Patch Network Auto-Reporter
============================

Automatically reports CLI errors to the shared HCS Patch Topic
when the patch network is enabled. Small agents cry for help —
coding agents watch the queue and fix the most common errors.

This module is called from cli/main.py process_input() error handler.
It is designed to be fast and non-blocking — errors in reporting
should never crash the CLI or slow down the user.

Enable:  ./launch.sh patch enable
Disable: ./launch.sh patch disable
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from src.logger import logger

_SETTINGS_FILE = Path(__file__).resolve().parent.parent / "data" / "settings.json"

# In-memory dedup cache: avoid spamming HCS with the same error repeatedly
# Key = error message hash, Value = timestamp of last report
_recent_reports: dict = {}
_DEDUP_WINDOW_SEC = 300  # Don't re-report the same error within 5 minutes


def is_enabled() -> bool:
    """Check if patch network auto-reporting is enabled in settings.json."""
    try:
        if _SETTINGS_FILE.exists():
            settings = json.loads(_SETTINGS_FILE.read_text())
            pn = settings.get("patch_network", {})
            return pn.get("enabled", False) and pn.get("auto_report_errors", False)
    except Exception:
        pass
    return False


def auto_report_error(app, command: str, error: str, stack_trace: str = None):
    """
    Fire-and-forget error report to HCS Patch Topic.

    Called from cli/main.py when a command fails. Runs in a background
    thread so it never blocks the CLI. Silently swallows all exceptions.

    Args:
        app: SpaceLordController instance (needs .hcs_manager and .account_id)
        command: The CLI command that failed (e.g. "swap 10 USDC for HBAR")
        error: The error message
        stack_trace: Optional full stack trace
    """
    if not is_enabled():
        return

    # Dedup: don't report the same error within 5 minutes
    import hashlib
    error_hash = hashlib.md5(error.encode()).hexdigest()[:12]
    now = datetime.now(timezone.utc).timestamp()
    last_report = _recent_reports.get(error_hash, 0)
    if now - last_report < _DEDUP_WINDOW_SEC:
        return
    _recent_reports[error_hash] = now

    # Run in background thread — never block the CLI
    thread = threading.Thread(
        target=_send_report,
        args=(app, command, error, stack_trace, error_hash),
        daemon=True,
    )
    thread.start()


def _send_report(app, command: str, error: str, stack_trace: str, error_hash: str):
    """Background thread: submit error report to HCS."""
    try:
        topic_id = _get_patch_topic_id()
        if not topic_id:
            return

        # Sanitise: strip any private keys, account secrets, file paths with /Users/
        sanitised_error = _sanitise(error)
        sanitised_command = _sanitise_command(command)
        sanitised_stack = _sanitise(stack_trace[:500]) if stack_trace else None

        payload = json.dumps({
            "type": "PATCH",
            "op": "report",
            "severity": "bug",
            "description": sanitised_error,
            "command": sanitised_command,
            "stack_hint": sanitised_stack,
            "error_hash": error_hash,
            "file": None,
            "diff": None,
            "patch_ref": None,
            "agent_id": getattr(app, 'account_id', 'unknown'),
            "version": "1.0.0-beta",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Use the app's HCS manager to submit
        if hasattr(app, 'hcs_manager') and app.hcs_manager:
            app.hcs_manager.submit_message(payload, topic_id=topic_id)
            logger.debug(f"[PatchNet] Auto-reported error: {error_hash}")
    except Exception as e:
        # Never crash the CLI — silently swallow
        logger.debug(f"[PatchNet] Auto-report failed (non-fatal): {e}")


def _get_patch_topic_id() -> str:
    """Get patch topic ID from env var or governance.json network section."""
    topic = os.getenv("PATCH_TOPIC_ID", "").strip().strip("'").strip('"')
    if topic:
        return topic
    topic = os.getenv("HCS_TOPIC_ID", "").strip().strip("'").strip('"')
    if topic:
        return topic
    # Try governance.json network section
    try:
        gov_path = Path(__file__).resolve().parent.parent / "data" / "governance.json"
        if gov_path.exists():
            with open(gov_path) as f:
                gov = json.load(f)
            net_topic = gov.get("network", {}).get("signal_topic", "")
            if net_topic:
                return net_topic
            return gov.get("hcs", {}).get("topic_id", "")
    except Exception:
        pass
    # NOTE: No hardcoded fallback here. Auto-reporting should only work
    # if the user has a configured topic. Reading uses patch CLI which
    # has its own fallback to the Space Lord network topic.
    return ""


def _sanitise(text: str) -> str:
    """Strip potentially sensitive data from error messages."""
    if not text:
        return text
    import re
    # Remove private keys (hex strings > 40 chars)
    text = re.sub(r'[0-9a-fA-F]{40,}', '[REDACTED_KEY]', text)
    # Remove /Users/xxx paths
    text = re.sub(r'/Users/[^\s/]+', '/Users/[REDACTED]', text)
    # Remove .env references with values
    text = re.sub(r'(PRIVATE_KEY|SECRET|TOKEN|PASSWORD)=[^\s]+', r'\1=[REDACTED]', text, flags=re.IGNORECASE)
    return text[:500]  # Cap length


def _sanitise_command(command: str) -> str:
    """Strip sensitive args from commands (e.g. send destinations, amounts)."""
    if not command:
        return command
    # Keep the command verb and token names, strip account IDs from send commands
    parts = command.split()
    if len(parts) > 0 and parts[0].lower() == "send":
        # "send 100 USDC to 0.0.xxxx" → "send [amount] USDC to [dest]"
        return "send [redacted]"
    return command[:100]
