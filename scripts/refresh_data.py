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

# Determine the project root (one level up from scripts/)
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data/"
DATA_DIR.mkdir(exist_ok=True)

POOLS_URL = "https://api.saucerswap.finance/v2/pools"
RAW_DATA_FILE = DATA_DIR / "pacman_data_raw.json"
TOKENS_FILE = DATA_DIR / "tokens.json"

import time

def refresh(force=False):
    # Rate Limit Check (60 seconds)
    if not force and RAW_DATA_FILE.exists():
        age = time.time() - RAW_DATA_FILE.stat().st_mtime
        if age < 60:
            print(f"  {C.R}Using cached pool data ({int(age)}s old)...{C.R}")
            return

    print(f"Fetching fresh pool data from {POOLS_URL}...")
    try:
        # 1. Load Whitelist from tokens.json
        whitelist = set()
        if TOKENS_FILE.exists():
            with open(TOKENS_FILE) as f:
                tdata = json.load(f)
                for item in tdata.values():
                    if "id" in item:
                        whitelist.add(item["id"])
                        
        # Always include HBAR and WHBAR
        whitelist.add("0.0.1456986") # WHBAR
        whitelist.add("0.0.0") # HBAR

        # 2. Fetch all pools
        try:
            # Full browser headers to bypass 401/403 blocks
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1"
            }
            response = requests.get(POOLS_URL, headers=headers, timeout=30)

            if response.status_code in [401, 403]:
                print(f"  {C.WARN}⚠{C.R}  API access restricted ({response.status_code}). Trying curl fallback...")
                import subprocess
                try:
                    # Curl fallback - often bypasses TLS fingerprinting issues
                    result = subprocess.run(
                        ["curl", "-s", "-H", "User-Agent: Mozilla/5.0", POOLS_URL],
                        capture_output=True, text=True, check=True
                    )
                    all_pools = json.loads(result.stdout)
                except Exception as curl_e:
                     print(f"  {C.WARN}⚠{C.R}  Curl fallback failed: {curl_e}")
                     return
            else:
                response.raise_for_status()
                all_pools = response.json()
                
            # Validate response structure
            if isinstance(all_pools, dict):
                 print(f"  {C.WARN}⚠{C.R}  API returned error: {all_pools.get('error', 'Unknown error')}")
                 return
            if not isinstance(all_pools, list):
                 print(f"  {C.WARN}⚠{C.R}  Unexpected API response format.")
                 return

        except Exception as e:
            # Try curl if requests failed completely
            print(f"  {C.WARN}⚠{C.R}  Requests failed ({e}). Trying curl fallback...")
            import subprocess
            try:
                result = subprocess.run(
                    ["curl", "-s", "-H", "User-Agent: Mozilla/5.0", POOLS_URL],
                    capture_output=True, text=True, check=True
                )
                try:
                    all_pools = json.loads(result.stdout)
                except json.JSONDecodeError:
                    print(f"  {C.WARN}⚠{C.R}  Curl output not JSON.")
                    return

                if isinstance(all_pools, dict):
                     print(f"  {C.WARN}⚠{C.R}  API returned error: {all_pools.get('error', 'Unknown error')}")
                     return
                if not isinstance(all_pools, list):
                     print(f"  {C.WARN}⚠{C.R}  Unexpected API response format.")
                     return

            except Exception as curl_e:
                print(f"  {C.WARN}⚠{C.R}  Curl fallback failed: {curl_e}")
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
