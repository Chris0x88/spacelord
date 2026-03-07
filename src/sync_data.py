#!/usr/bin/env python3
"""
Pacman Data Sync
================
Called at startup to ensure tokens.json is in sync with
pacman_data_raw.json (the cached pool data from last refresh).

This is a fast, offline operation — no API calls.
For a full refresh from SaucerSwap, run: scripts/refresh_data.py
"""

import json
from pathlib import Path
from src.logger import logger

def sync_saucerswap_v2():
    """
    Ensure tokens.json contains every token that appears in the cached pool data.
    Also ensures NLP aliases (BITCOIN, ETH, etc.) are present.
    Fast — only reads local files, no network calls.
    """
    raw_path    = Path("data/pacman_data_raw.json")
    tokens_path = Path("data/tokens.json")

    if not raw_path.exists() or not tokens_path.exists():
        logger.warning("[Sync] Missing data files — skipping token sync.")
        return

    with open(raw_path) as f:
        pools = json.load(f)
    with open(tokens_path) as f:
        tokens = json.load(f)

    existing_ids = {meta.get("id") for meta in tokens.values() if meta.get("id")}
    added = 0

    for pool in pools:
        for side in ["tokenA", "tokenB"]:
            t = pool.get(side)
            if not isinstance(t, dict):
                continue
            tid = t.get("id")
            if not tid or tid in existing_ids:
                continue

            sym = (t.get("symbol") or "UNKNOWN").strip()
            key = sym.upper()
            if key in tokens:
                key = f"{sym.upper()}_{tid.split('.')[-1]}"

            tokens[key] = {
                "id": tid,
                "decimals": t.get("decimals", 8),
                "symbol": sym,
                "name": t.get("name", sym),
                "icon": t.get("icon", ""),
            }
            existing_ids.add(tid)
            added += 1

    if added > 0:
        with open(tokens_path, "w") as f:
            json.dump(tokens, f, indent=2)
        logger.info(f"[Sync] Added {added} new tokens to registry ({len(tokens)} total).")
    else:
        logger.debug("[Sync] Token registry already up to date.")

if __name__ == "__main__":
    sync_saucerswap_v2()
