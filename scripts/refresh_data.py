#!/usr/bin/env python3
"""
Refresh Data Script
===================

Downloads fresh pool data from SaucerSwap V2 API and rebuilds the routing table.
"""

import json
import requests
import sys
import os
import argparse
from pathlib import Path

# --- THE "WHY" ---
# WHAT: This script fetches live pool data from SaucerSwap V2.
# WHY: Pacman is a "data-led" agent. To find the best routes and prices, 
# it needs a local map of liquidity. We download this "raw" data 
# and then filter it to keep our routing graph lean and high-confidence.
# 
# CURATION: We only track pools involving tokens we "know" (in tokens.json). 
# This prevents the router from selecting low-liquidity, high-slippage 
# "garbage" pools and protects against API rate limits.
# -----------------

class C:
    R = "\033[0m"
    WARN = "\033[93m"
    OK = "\033[92m"
    BOLD = "\033[1m"

POOLS_URL = "https://api.saucerswap.finance/v2/pools"

# Robust absolute path resolution
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_FILE = DATA_DIR / "pacman_data_raw.json"
TOKENS_FILE = DATA_DIR / "tokens.json"
POOLS_REGISTRY_FILE = DATA_DIR / "pools.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

def refresh(full_fetch=False):
    print(f"\n  {C.BOLD}🔄 Refreshing SaucerSwap V2 Data{C.R}")
    print(f"  Source: {POOLS_URL}")
    
    try:
        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)

        # 1. Load Curation Rules from Settings
        settings = {}
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE) as f:
                    settings = json.load(f)
            except: pass
        
        refresh_rules = settings.get("refresh_rules", {})
        # If strategy is "comprehensive", we fetch all pools (matching min_liquidity if we added that)
        # Otherwise "curated" (registry only)
        strategy = refresh_rules.get("strategy", "curated")
        always_include = refresh_rules.get("always_include_ids", ["0.0.0", "0.0.1456986"])

        # 2. Build Whitelist
        whitelist = set(always_include)
        
        # Add Curated Tokens
        if TOKENS_FILE.exists():
            try:
                with open(TOKENS_FILE) as f:
                    tdata = json.load(f)
                    for item in tdata.values():
                        if "id" in item: whitelist.add(item["id"])
            except Exception: pass
            
        # Add Registered Pools
        if POOLS_REGISTRY_FILE.exists():
            try:
                with open(POOLS_REGISTRY_FILE) as f:
                    pdata = json.load(f)
                    for pool in pdata:
                        whitelist.add(pool.get("tokenA"))
                        whitelist.add(pool.get("tokenB"))
            except Exception: pass

        whitelist.discard(None)

        # 3. Fetch all pools from SaucerSwap V2 API
        try:
            response = requests.get(POOLS_URL, timeout=30)
            if response.status_code == 401:
                print(f"  {C.WARN}⚠{C.R} API access restricted (401). Using cached data.")
                return
            response.raise_for_status()
            all_pools = response.json()
        except Exception as e:
            print(f"  {C.WARN}⚠{C.R} API fetch failed ({e}). Protecting cached data.")
            return
        
        # 4. Filter Based on Strategy
        relevant_pools = []
        if full_fetch or strategy == "comprehensive":
            print(f"  {C.OK}✓{C.R} Full/Comprehensive download. No curation.")
            relevant_pools = all_pools
        else:
            # Curated Mode: Keep pool only if BOTH tokens are in our curated whitelist
            # WHY: This ensures the router only sees pools that we have verified metadata for.
            for pool in all_pools:
                ta = pool.get("tokenA", {}).get("id")
                tb = pool.get("tokenB", {}).get("id")
                
                if ta in whitelist and tb in whitelist:
                    relevant_pools.append(pool)
        
        # 5. Save to Disk
        if relevant_pools:
            with open(RAW_DATA_FILE, "w") as f:
                json.dump(relevant_pools, f, indent=2)
            print(f"  {C.OK}✓{C.R} Saved {len(relevant_pools)} pools to {RAW_DATA_FILE}")
        else:
            print(f"  {C.WARN}⚠{C.R} No pools matched criteria. Source data preserved.")
            
    except Exception as e:
        print(f"  {C.WARN}⚠{C.R} Fatal error in refresh: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refresh SaucerSwap V2 Data")
    parser.add_argument("--full", action="store_true", help="Download all pools (skip curation)")
    args = parser.parse_args()
    
    refresh(full_fetch=args.full)
