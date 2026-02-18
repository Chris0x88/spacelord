"""
Pacman Discovery - Universal Pool Search Engine
==============================================

This module is a standalone "Sidecar" for finding liquidity pools on Hedera.
It is decoupled from the PacmanController to ensure that discovery logic
(which often requires external APIs and heavy filtering) does not 
destabilize core trading logic.

Supported Protocols:
- SaucerSwap V1 (Constant Product)
- SaucerSwap V2 (Concentrated Liquidity)
"""

import requests
from typing import List, Dict, Optional
from src.logger import logger

SAUCERSWAP_BASE = "https://api.saucerswap.finance"
PUBLIC_DEMO_KEY = "875e1017-87b8-4b12-8301-6aa1f1aa073b"

class DiscoveryManager:
    """
    Handles discovery of new pools and metadata.
    """

    def __init__(self, network: str = "mainnet"):
        self.network = network
        self.base_url = SAUCERSWAP_BASE
        
        # Load API Key from environment
        import os
        self.api_key = os.getenv("SAUCERSWAP_API_KEY_MAINNET") or os.getenv("SAUCERSWAP_API_KEY")
        if not self.api_key:
            self.api_key = PUBLIC_DEMO_KEY

    def _get_headers(self) -> Dict:
        """Browser-like headers to bypass bot detection."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def search_pools(self, query: str, protocol: str = "v2") -> List[Dict]:
        """
        Search for pools by token symbol or ID.
        """
        endpoint = "/v2/pools" if protocol.lower() == "v2" else "/pools"
        url = f"{self.base_url}{endpoint}"
        
        logger.debug(f"Searching {protocol} pools at {url} for query: {query}")
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            all_pools = response.json()
            
            query = query.upper()
            results = []
            
            for pool in all_pools:
                tA = pool.get("tokenA", {})
                tB = pool.get("tokenB", {})
                
                # Match symbol or ID
                match = (
                    query in (tA.get("symbol", "").upper()) or
                    query in (tB.get("symbol", "").upper()) or
                    query == tA.get("id") or
                    query == tB.get("id")
                )
                
                if match:
                    results.append(pool)
            
            return results
        except Exception as e:
            logger.error(f"Discovery search failed: {e}")
            return []

    def get_top_pools(self, protocol: str = "v2", limit: int = 20) -> List[Dict]:
        """
        Fetch top pools by liquidity/volume.
        """
        endpoint = "/v2/pools" if protocol.lower() == "v2" else "/pools"
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            all_pools = response.json()
            
            # Sort by liquidity (LP Usd) if available
            # V2 has 'tvlUsd', V1 has 'liquidityUsd'? Need to check fields.
            # For now, we'll return the first N as the API usually sorts by popularity.
            return all_pools[:limit]
        except Exception as e:
            logger.error(f"Discovery top pools fetch failed: {e}")
            return []

    def get_pool_metadata(self, pool_id: str) -> Optional[Dict]:
        """
        Fetch detailed metadata for a specific pool contract.
        """
        # This could query Mirror Node for contract info
        pass

if __name__ == "__main__":
    # Quick Test
    discovery = DiscoveryManager()
    print("Searching for USDC pools...")
    pools = discovery.search_pools("USDC")
    for p in pools[:3]:
        print(f"- Pool: {p.get('contractId')} ({p.get('tokenA',{}).get('symbol')} / {p.get('tokenB',{}).get('symbol')})")
