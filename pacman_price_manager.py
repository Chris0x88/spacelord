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
from typing import Dict, Optional

class PacmanPriceManager:
    def __init__(self, data_file: str = "pacman_data_raw.json"):
        self.data_file = data_file
        self.prices: Dict[str, float] = {}
        self.hbar_price: float = 0.0
        self._load_data()

    def _load_data(self):
        """Loads raw pool data and builds price map from SaucerSwap V2 export."""
        try:
            self.prices = {}
            
            # 1. Primary: pacman_data_raw.json
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    pools = json.load(f)
                for pool in pools:
                    for key in ["tokenA", "tokenB"]:
                        t = pool.get(key, {})
                        if t.get("id"):
                            price = float(t.get("priceUsd", 0))
                            if price > 0: self.prices[t["id"]] = price

            # 2. Secondary: tokens.json
            if os.path.exists("tokens.json"):
                with open("tokens.json", 'r') as f:
                    tokens_meta = json.load(f)
                for meta in tokens_meta.values():
                    tid = meta.get("id")
                    price = float(meta.get("priceUsd", 0))
                    if tid and price > 0 and tid not in self.prices:
                        self.prices[tid] = price

            # 3. HBAR Resolution
            if "0.0.1456986" in self.prices:
                self.hbar_price = self.prices["0.0.1456986"]
            elif "0.0.0" in self.prices:
                self.hbar_price = self.prices["0.0.0"]
                
        except Exception as e:
            print(f"⚠️ Price Manager Load Error: {e}")

    def get_price(self, token_id: str) -> float:
        """Get USD price for a token ID (or HBAR/0.0.0)."""
        # Normalization
        tid = token_id.lower()
        
        # HBAR Handling
        if tid in ["hbar", "0.0.0"]:
            return self.hbar_price
            
        # WHBAR Handling (if passed explicitly)
        if tid == "0.0.1456986":
            return self.prices.get("0.0.1456986", self.hbar_price)

        # Standard Lookup
        return self.prices.get(token_id, 0.0)

    def get_hbar_price(self) -> float:
        return self.hbar_price

    def reload(self):
        """Force reload from disk (useful after refresh_data.py runs)."""
        self._load_data()

# Singleton
price_manager = PacmanPriceManager()
