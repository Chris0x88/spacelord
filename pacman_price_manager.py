"""
Pacman Price Manager
====================

Manages token prices using local pool data (pacman_data_raw.json)
as the Source of Truth. This aligns with the "refresh loop" architecture.

Usage:
    from pacman_price_manager import price_manager
    price = price_manager.get_price("0.0.456858")
"""

import json
import os

class PacmanPriceManager:
    """
    Manages token prices by aggregating data from local sources.
    
    The manager uses `pacman_data_raw.json` (SaucerSwap V2 live export) 
    as the sole source of truth for pricing.
    """

    def __init__(self, data_file: str = "pacman_data_raw.json"):
        """
        Initialize the price manager.
        
        Args:
            data_file: Path to the raw pool data file.
        """
        self.data_file = data_file
        self.prices: Dict[str, float] = {}
        self.sources: Dict[str, str] = {}
        self.hbar_price: float = 0.0
        self._load_data()

    def _load_data(self) -> None:
        """
        Load raw pool data and build a price map.
        
        This method processes `pacman_data_raw.json` as the source of truth.
        """
        try:
            self.prices = {}
            self.sources = {}
            if not os.path.exists(self.data_file):
                return

            with open(self.data_file, 'r') as f:
                pools = json.load(f)
            
            for pool in pools:
                pool_id = pool.get("contractId", "Unknown Pool")
                for key in ["tokenA", "tokenB"]:
                    t = pool.get(key, {})
                    tid = t.get("id")
                    if tid:
                        try:
                            price = float(t.get("priceUsd", 0))
                            if price > 0:
                                # Prioritize source if it provides a better price
                                if price > self.prices.get(tid, 0):
                                    self.prices[tid] = price
                                    self.sources[tid] = f"SaucerSwap V2 (Contract ID: {pool_id})"

                                # Check for HBAR-USDC pool (USDC is 0.0.456858, WHBAR is 0.0.1456986)
                                # We use this as the source for Native HBAR
                                if (t.get("id") == "0.0.1456986" and 
                                    (pool.get("tokenA", {}).get("id") == "0.0.456858" or 
                                     pool.get("tokenB", {}).get("id") == "0.0.456858")):
                                    self.sources["0.0.0"] = f"SaucerSwap V2 (Contract ID: {pool_id})"

                        except (ValueError, TypeError):
                            continue

            # Resolve Native HBAR Price (from WHBAR 0.0.1456986)
            self.hbar_price = self.prices.get("0.0.1456986", 0.0)
            # If we didn't find the specific USDC pool, fall back to WHBAR's source
            if self.hbar_price > 0 and "0.0.0" not in self.sources:
                self.sources["0.0.0"] = self.sources.get("0.0.1456986", "SaucerSwap V2")
                
        except Exception as e:
            print(f"⚠️ Price Manager Load Error: {e}")

    def get_price(self, token_id: str) -> float:
        """Get USD price for a token."""
        return self.get_price_with_source(token_id)[0]

    def get_price_with_source(self, token_id: str) -> tuple[float, str]:
        """
        Get USD price and its source for a given token ID.
        
        Returns:
            (price, source)
        """
        tid = token_id.lower()
        
        if tid in ["hbar", "0.0.0"]:
            return self.hbar_price, self.sources.get("0.0.0", "SaucerSwap V2")
            
        # if tid == "0.0.1456986":
        #    return self.get_price_with_source("0.0.1456986") # recursive but handled in get call

        price = self.prices.get(token_id, 0.0)
        source = self.sources.get(token_id, "Unknown")
        return price, source

    def get_hbar_price(self) -> float:
        """Get the current live price of native HBAR."""
        return self.hbar_price

    def reload(self) -> None:
        """Force a reload of data from the disk."""
        self._load_data()

# Singleton
price_manager = PacmanPriceManager()
