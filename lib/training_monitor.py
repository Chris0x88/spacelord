#!/usr/bin/env python3
"""
Training Data Monitor
=====================

Ensures the knowledge harvest runs periodically so training data stays fresh.
Called from the daemon heartbeat loop and optionally from CLI on startup.

The harvest converts data/knowledge/incidents/*.json into training pairs.
If it hasn't run in 24 hours, this module triggers it automatically.
"""

import time
from pathlib import Path
from src.logger import logger

ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = ROOT / "training_data"
ERROR_FIX_FILE = TRAINING_DIR / "error_fix_pairs.jsonl"
INCIDENTS_DIR = ROOT / "data" / "knowledge" / "incidents"
HARVEST_INTERVAL_SEC = 86400  # 24 hours

# In-memory tracker so we don't check filesystem every command
_last_check = 0
_CHECK_COOLDOWN = 3600  # Only check once per hour


def check_and_harvest_if_stale():
    """
    Check if training data harvest is stale. If so, run it.
    Safe to call frequently — has an in-memory cooldown.
    """
    global _last_check
    now = time.monotonic()
    if now - _last_check < _CHECK_COOLDOWN:
        return
    _last_check = now

    try:
        # Check if incidents exist but error_fix_pairs is stale
        if not INCIDENTS_DIR.exists():
            return

        incident_count = len(list(INCIDENTS_DIR.glob("*.json")))
        if incident_count == 0:
            return

        # Check when error_fix_pairs was last modified
        if ERROR_FIX_FILE.exists():
            mtime = ERROR_FIX_FILE.stat().st_mtime
            age_sec = time.time() - mtime
            if age_sec < HARVEST_INTERVAL_SEC:
                return  # Fresh enough

        # Also check: are there more incidents than error_fix lines?
        ef_count = 0
        if ERROR_FIX_FILE.exists():
            with open(ERROR_FIX_FILE) as f:
                ef_count = sum(1 for _ in f)

        if ef_count >= incident_count and ERROR_FIX_FILE.exists():
            return  # All incidents already harvested

        # Stale or incomplete — run harvest
        logger.debug(f"[TrainingMonitor] Harvest stale ({ef_count} pairs, {incident_count} incidents). Running...")
        _run_harvest()

    except Exception as e:
        logger.debug(f"[TrainingMonitor] Check failed (non-fatal): {e}")


def _run_harvest():
    """Run the knowledge harvest script."""
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "scripts.harvest_knowledge", "--backfill"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.debug("[TrainingMonitor] Harvest completed successfully")
        else:
            logger.debug(f"[TrainingMonitor] Harvest failed: {result.stderr[:200]}")
    except Exception as e:
        logger.debug(f"[TrainingMonitor] Harvest exec failed: {e}")
