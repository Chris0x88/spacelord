#!/usr/bin/env python3
"""
Agent Interaction Logger
========================

Structured JSONL logging of every command the app processes.
Enables autonomous debugging: read logs → identify failures → fix.

Log file: logs/agent_interactions.jsonl  (gitignored via logs/)
Format:   One JSON object per line — machine-parseable, appendable, grep-friendly
Bounded:  Max 5000 entries (~2.5 MB), then prune oldest to monthly archive
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "agent_interactions.jsonl"
MAX_ENTRIES = 5000
PRUNE_KEEP = 1000  # Keep newest 1000 when pruning


def _ensure_dir():
    LOG_DIR.mkdir(exist_ok=True)


def log_interaction(command: str, resolved: dict = None, result: str = "unknown",
                    error: str = None, duration_ms: float = 0, source: str = "unknown"):
    """Append one interaction entry to the JSONL log."""
    _ensure_dir()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "resolved": resolved,
        "result": result,
        "error": error,
        "duration_ms": round(duration_ms, 1),
        "source": source,
    }
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass  # Never let logging break the app

    # Prune periodically (check every 100 writes to avoid overhead)
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 3_000_000:  # ~3 MB trigger
            prune_if_needed()
    except Exception:
        pass


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
        # Group by first 80 chars of error to cluster similar failures
        key = err[:80] if err else "unknown"
        if key not in summary:
            summary[key] = {"count": 0, "last_ts": None, "example_command": None}
        summary[key]["count"] += 1
        summary[key]["last_ts"] = f.get("ts")
        summary[key]["example_command"] = f.get("command")
    return summary


def prune_if_needed():
    """Rotate old entries to monthly archive, keep newest PRUNE_KEEP in active log."""
    if not LOG_FILE.exists():
        return
    try:
        lines = LOG_FILE.read_text().strip().split("\n")
        if len(lines) <= MAX_ENTRIES:
            return

        # Archive the oldest entries
        archive_lines = lines[:-PRUNE_KEEP]
        keep_lines = lines[-PRUNE_KEEP:]

        month_tag = datetime.now().strftime("%Y-%m")
        archive_file = LOG_DIR / f"agent_interactions.{month_tag}.archive.jsonl"
        with open(archive_file, "a") as f:
            f.write("\n".join(archive_lines) + "\n")

        # Rewrite active log with only recent entries
        LOG_FILE.write_text("\n".join(keep_lines) + "\n")
    except Exception:
        pass  # Never break the app over log maintenance
