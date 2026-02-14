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
from pathlib import Path

class C:
    R = "\033[0m"
    WARN = "\033[93m"

POOLS_URL = "https://api.saucerswap.finance/v2/pools"
RAW_DATA_FILE = Path(__file__).parent / "pacman_data_raw.json"

def refresh():
    print(f"Fetching fresh pool data from {POOLS_URL}...")
    try:
        # 1. Load Whitelist from tokens.json
        tokens_file = Path(__file__).parent / "tokens.json"
        whitelist = set()
        if tokens_file.exists():
            with open(tokens_file) as f:
                tdata = json.load(f)
                for item in tdata.values():
                    if "id" in item:
                        whitelist.add(item["id"])
                        
        # Always include HBAR and WHBAR
        whitelist.add("0.0.1456986") # WHBAR
        whitelist.add("0.0.0") # HBAR

        # 2. Fetch all pools
        try:
            response = requests.get(POOLS_URL, timeout=30)
            if response.status_code == 401:
                print(f"  {C.WARN}⚠{C.R}  API access restricted (401). Using cached data.")
                return
            response.raise_for_status()
            all_pools = response.json()
        except Exception as e:
            print(f"  {C.WARN}⚠{C.R}  API fetch failed ({e}). Using cached data.")
            return
        
        # 3. Filter relevant pools
        # Keep pool if EITHER token is in our whitelist
        relevant_pools = []
        for pool in all_pools:
            ta = pool.get("tokenA", {}).get("id")
            tb = pool.get("tokenB", {}).get("id")
            
            if ta in whitelist or tb in whitelist:
                relevant_pools.append(pool)
        
        # 4. Save
        with open(RAW_DATA_FILE, "w") as f:
            json.dump(relevant_pools, f, indent=2)
            
        print(f"Fetched {len(all_pools)} pools, saved {len(relevant_pools)} relevant to {RAW_DATA_FILE}")
        
    except Exception as e:
        print(f"⚠️  Fatal error in refresh: {e}")
        # Don't exit, just let the app use old data if fetch fails

if __name__ == "__main__":
    refresh()
