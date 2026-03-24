#!/usr/bin/env python3
"""
Agent Interaction Logger + Training Data Pipeline
===================================================

Three output streams, each serving a different purpose:

1. logs/agent_interactions.jsonl
   - Raw operational log of every command: input, output, errors, timing
   - Used for autonomous debugging (agent reads these to self-diagnose)
   - Bounded: 5000 entries max, then prune to monthly archive

2. training_data/instruction_pairs.jsonl
   - SFT (Supervised Fine-Tuning) format: system → user → assistant → result
   - Each entry is a complete conversation turn suitable for fine-tuning
   - Accumulated forever (this is the gold — never auto-prune)

3. training_data/preference_pairs.jsonl
   - DPO (Direct Preference Optimization) format: prompt → chosen → rejected
   - Generated from incidents/antipatterns by harvest_knowledge.py
   - Also accumulated forever

Log file locations are all gitignored (logs/ and training_data/).
"""

import io
import json
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "agent_interactions.jsonl"
TRAINING_DIR = ROOT / "training_data"
SFT_FILE = TRAINING_DIR / "instruction_pairs.jsonl"

MAX_ENTRIES = 5000
PRUNE_KEEP = 1000


def _ensure_dirs():
    LOG_DIR.mkdir(exist_ok=True)
    TRAINING_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Output capture context manager
# ---------------------------------------------------------------------------

class _OutputCapture:
    """Captures stdout while still printing to the real terminal."""
    def __init__(self):
        self.buffer = io.StringIO()
        self._original = None

    def start(self):
        self._original = sys.stdout
        sys.stdout = self

    def stop(self):
        if self._original:
            sys.stdout = self._original

    def write(self, s):
        self.buffer.write(s)
        if self._original:
            self._original.write(s)

    def flush(self):
        if self._original:
            self._original.flush()

    def fileno(self):
        if self._original:
            return self._original.fileno()
        raise io.UnsupportedOperation("fileno")

    def isatty(self):
        if self._original:
            return self._original.isatty()
        return False

    def get_output(self) -> str:
        return self.buffer.getvalue()


@contextmanager
def capture_output():
    """Context manager that captures stdout while still displaying it."""
    cap = _OutputCapture()
    cap.start()
    try:
        yield cap
    finally:
        cap.stop()


# ---------------------------------------------------------------------------
# Core logging
# ---------------------------------------------------------------------------

def log_interaction(command: str, resolved: dict = None, result: str = "unknown",
                    error: str = None, duration_ms: float = 0, source: str = "unknown",
                    output: str = None, stack_trace: str = None,
                    account_id: str = None):
    """Append one interaction entry to the operational JSONL log."""
    _ensure_dirs()

    # Truncate output to prevent log bloat (keep first + last 500 chars)
    output_trimmed = None
    if output:
        output = _strip_ansi(output).strip()
        if len(output) > 1200:
            output_trimmed = output[:500] + "\n...[truncated]...\n" + output[-500:]
        else:
            output_trimmed = output

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "resolved": resolved,
        "result": result,
        "error": error,
        "stack_trace": stack_trace[:500] if stack_trace else None,
        "output": output_trimmed,
        "duration_ms": round(duration_ms, 1),
        "source": source,
        "account_id": account_id,
    }
    # Strip None values to keep JSONL compact
    entry = {k: v for k, v in entry.items() if v is not None}

    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass

    # Also emit SFT training pair for swap/send/associate commands
    if _is_trainable_command(command):
        _emit_sft_pair(command, resolved, result, error, output_trimmed, source, account_id)

    # Prune check (every ~3 MB)
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 3_000_000:
            prune_if_needed()
    except Exception:
        pass


def _is_trainable_command(command: str) -> bool:
    """Should this command generate a training pair?"""
    cmd_lower = command.lower().strip()
    trainable_prefixes = [
        "swap", "send", "balance", "price", "associate", "assoc",
        "account", "robot", "history", "stake", "unstake",
        "pool-deposit", "pool-withdraw", "lp", "order",
        "fund", "doctor", "status", "info", "whoami",
    ]
    # Also capture NLP-style commands (start with amounts or token names)
    first_word = cmd_lower.split()[0] if cmd_lower.split() else ""
    return (first_word in trainable_prefixes or
            first_word.replace(".", "").isdigit() or  # "10 USDC for HBAR"
            any(cmd_lower.startswith(p) for p in ["buy ", "sell "]))


def _emit_sft_pair(command: str, resolved: dict, result: str, error: str,
                   output: str, source: str, account_id: str):
    """Write one SFT instruction pair to training_data/instruction_pairs.jsonl.

    Format is OpenAI-compatible messages array, ready for fine-tuning.
    """
    _ensure_dirs()

    # Build the system message (compact version of SKILL.md essentials)
    system_msg = (
        "You are driving the Space Lord Hedera trading CLI. "
        "Commands: swap <amt> <FROM> for <TO>, balance, send <amt> <TOKEN> to <ACCOUNT>, "
        "price <TOKEN>, associate <TOKEN>, account switch <ID>, robot status, history. "
        "Use token tickers (HBAR, USDC, WBTC, SAUCE, USDC[hts]). "
        "V2 is the only routing protocol. Never simulate. "
        "Safety limits: $100 max swap, $100 daily, 5% max slippage."
    )

    # Build assistant turn (what the CLI actually produced)
    assistant_content = ""
    if output:
        # Keep output compact for training
        assistant_content = output[:800]
    elif result == "success":
        assistant_content = f"[Command executed successfully]"
    elif error:
        assistant_content = f"[Error: {error}]"
    else:
        assistant_content = "[No output captured]"

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": command},
        {"role": "assistant", "content": assistant_content},
    ]

    # Add metadata (not part of training messages, but useful for filtering)
    entry = {
        "messages": messages,
        "metadata": {
            "ts": datetime.now(timezone.utc).isoformat(),
            "result": result,
            "error": error,
            "resolved": resolved,
            "account_id": account_id,
            "source": source,
            "duration_ms": 0,  # Filled by caller if available
        }
    }

    try:
        with open(SFT_FILE, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# ANSI stripping
# ---------------------------------------------------------------------------

import re
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


# ---------------------------------------------------------------------------
# Querying (for autonomous debugging)
# ---------------------------------------------------------------------------

def get_recent(n: int = 50) -> list:
    """Read the last N interaction entries."""
    if not LOG_FILE.exists():
        return []
    try:
        lines = LOG_FILE.read_text().strip().split("\n")
        entries = []
        for line in lines[-n:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries
    except Exception:
        return []


def get_failure_summary() -> dict:
    """Aggregate recent errors by type for autonomous debugging."""
    entries = get_recent(200)
    failures = [e for e in entries if e.get("result") == "error"]
    summary = {}
    for f in failures:
        err = f.get("error", "unknown")
        key = err[:80] if err else "unknown"
        if key not in summary:
            summary[key] = {"count": 0, "last_ts": None, "example_command": None}
        summary[key]["count"] += 1
        summary[key]["last_ts"] = f.get("ts")
        summary[key]["example_command"] = f.get("command")
    return summary


# ---------------------------------------------------------------------------
# Pruning
# ---------------------------------------------------------------------------

def prune_if_needed():
    """Rotate old entries to monthly archive, keep newest PRUNE_KEEP in active log."""
    if not LOG_FILE.exists():
        return
    try:
        lines = LOG_FILE.read_text().strip().split("\n")
        if len(lines) <= MAX_ENTRIES:
            return
        archive_lines = lines[:-PRUNE_KEEP]
        keep_lines = lines[-PRUNE_KEEP:]
        month_tag = datetime.now().strftime("%Y-%m")
        archive_file = LOG_DIR / f"agent_interactions.{month_tag}.archive.jsonl"
        with open(archive_file, "a") as f:
            f.write("\n".join(archive_lines) + "\n")
        LOG_FILE.write_text("\n".join(keep_lines) + "\n")
    except Exception:
        pass
