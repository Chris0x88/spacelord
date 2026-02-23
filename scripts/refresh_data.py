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
    OK = "\033[92m"

from src.logger import logger

# Determine the project root (one level up from scripts/)
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data/"
DATA_DIR.mkdir(exist_ok=True)

POOLS_URL = "https://api.saucerswap.finance/v2/pools"
RAW_DATA_FILE = DATA_DIR / "pacman_data_raw.json"
TOKENS_FILE = DATA_DIR / "tokens.json"

# Official SaucerSwap Demo Key (Publicly available in docs)
# Used as fallback if user has not configured their own in .env
PUBLIC_DEMO_KEY = "875e1017-87b8-4b12-8301-6aa1f1aa073b"

import time

def load_env():
    """Load variables from .env file into os.environ."""
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value

def refresh(force=False):
    load_env()
    network = os.getenv("PACMAN_NETWORK", "mainnet").lower()
    
    # Get API Key
    if network == "testnet":
        api_key = os.getenv("SAUCERSWAP_API_KEY_TESTNET")
    else:
        api_key = os.getenv("SAUCERSWAP_API_KEY_MAINNET")
        
    # ABSOLUTELY CRITICAL FALLBACK: Use Demo Key if no private key provided
    if not api_key:
        api_key = PUBLIC_DEMO_KEY
        logger.info("[Refresh] Using Public Fallback (Demo Key)")
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

        # 2. Fetch all pools (V1 and V2)
        all_pools = []
        endpoints = [
            ("V2", "https://api.saucerswap.finance/v2/pools"),
            ("V1", "https://api.saucerswap.finance/pools")
        ]

        def fetch_url(url, label):
            import subprocess
            
            # Helper for curl
            def run_curl(target_url):
                try:
                    cmd = ["curl", "-s", "-L"]
                    if api_key:
                         cmd.extend(["-H", f"x-api-key: {api_key}"])
                    cmd.extend(["-H", "User-Agent: Mozilla/5.0", target_url])
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    if not result.stdout.strip():
                        return None
                    return json.loads(result.stdout)
                except Exception as e:
                    print(f"  {C.WARN}⚠{C.R}  Curl failed for {label}: {e}")
                    return None

            try:
                # 1. Try requests first
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                if api_key:
                    headers["x-api-key"] = api_key

                response = requests.get(url, headers=headers, timeout=12)
                if response.status_code == 200:
                    try:
                        return response.json()
                    except:
                        # Fallback to curl if not JSON
                        return run_curl(url)
                else:
                    return run_curl(url)
            except Exception as e:
                # 2. Hard fallback to curl
                return run_curl(url)

        for label, url in endpoints:
            print(f"Fetching fresh {label} pool data...")
            result = fetch_url(url, label)
            if isinstance(result, list):
                all_pools.extend(result)
            else:
                print(f"  {C.WARN}⚠{C.R}  Unexpected {label} response format.")
        
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
    import sys
    force = "--force" in sys.argv
    refresh(force=force)
