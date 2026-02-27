#!/usr/bin/env python3
"""
Pacman Data Sync
================
Syncs high-liquidity pools and tokens from SaucerSwap data
and ensures tokens.json is unified with pacman_data_raw.json.
"""

import json
import requests
from pathlib import Path
from src.logger import logger

def sync_saucerswap_v2():
    logger.info("📡 Refreshing data from Mirror Node and internal registries...")
    
    raw_path = Path("data/pacman_data_raw.json")
    tokens_path = Path("data/tokens.json")
    
    if not raw_path.exists() or not tokens_path.exists():
        logger.error("Missing data files. Restore from git first.")
        return

    with open(raw_path) as f:
        existing_raw = json.load(f)
    with open(tokens_path) as f:
        existing_tokens = json.load(f)

    existing_token_ids = {t['id'] for t in existing_tokens.values()}
    added_tokens = 0

    for pool in existing_raw:
        for key in ['tokenA', 'tokenB']:
            t = pool.get(key)
            if not t or not isinstance(t, dict): continue
            
            tid = t.get('id')
            if tid and tid not in existing_token_ids:
                sym = t.get('symbol', 'UNKNOWN').upper()
                # Clean up symbol for registry key
                if sym in existing_tokens:
                    sym = f"{sym}_{tid.split('.')[-1]}"
                
                existing_tokens[sym] = {
                    "id": tid,
                    "decimals": t.get('decimals', 8),
                    "symbol": t.get('symbol', sym),
                    "name": t.get('name', sym)
                }
                existing_token_ids.add(tid)
                added_tokens += 1

    if added_tokens > 0:
        with open(tokens_path, "w") as f:
            json.dump(existing_tokens, f, indent=2)
        logger.info(f"✅ Sync Complete: Unified {added_tokens} missing tokens into registry.")
    else:
        logger.info("✅ Sync Complete: Registry is already unified with raw data.")

if __name__ == "__main__":
    sync_saucerswap_v2()
