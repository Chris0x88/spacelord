#!/usr/bin/env python3
"""
Refresh Data Script
===================

Downloads fresh pool data from SaucerSwap V2 API and rebuilds the routing table.
"""

import json
import requests
import sys
from pathlib import Path

POOLS_URL = "https://api.saucerswap.finance/v2/pools"
RAW_DATA_FILE = Path(__file__).parent / "pacman_data_raw.json"

def refresh():
    print(f"Fetching fresh pool data from {POOLS_URL}...")
    try:
        response = requests.get(POOLS_URL, timeout=30)
        response.raise_for_status()
        pools = response.json()
        
        with open(RAW_DATA_FILE, "w") as f:
            json.dump(pools, f, indent=2)
            
        print(f"Successfully saved {len(pools)} pools to {RAW_DATA_FILE}")
        
        # Now trigger the build
        print("Rebuilding routes...")
        import build_routes
        build_routes.build_route_table()
        
        print("Done!")
        
    except Exception as e:
        print(f"Error refreshing data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    refresh()
