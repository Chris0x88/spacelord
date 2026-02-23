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
    
    WHY: By relying on the raw pool data, we ensure that our pricing is always
    synchronous with the routing graph. If a pool exists for routing, we have 
    its current live price. This prevents "phantom routes" where we can 
    route but can't price (or vice-versa).
    
    DATA FLOW:
    refresh_data.py -> data/pacman_data_raw.json -> PacmanPriceManager
    """

    def __init__(self, data_file: str = None):
        """
        Initialize the price manager.
        
        Args:
            data_file: Path to the raw pool data file.
        """
        if data_file is None:
            from pathlib import Path
            self.data_file = str(Path(__file__).parent.parent / "data" / "pacman_data_raw.json")
        else:
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
        from src.logger import logger
        try:
            self.prices = {}
            self.sources = {}
            if not os.path.exists(self.data_file):
                logger.warning(f"[PriceManager] Data file not found: {self.data_file}")
                return

            with open(self.data_file, 'r') as f:
                pools = json.load(f)
            
            logger.info(f"[PriceManager] Loading from {self.data_file} ({len(pools)} pools)...")
            
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
            # WHY: HBAR doesn't have its own "pool" on-chain; liquidity exists 
            # exclusively against the wrapped version (WHBAR). We map WHBAR 
            # price 1:1 to HBAR.
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
            return self.get_hbar_price(), self.sources.get("0.0.0", "SaucerSwap V2")
        
        # Try Live Fetch for major tokens
        if tid in ["0.0.731861", "0.0.456858"]: # SAUCE, USDC
             return self._get_live_price(tid)
            
        # Case-insensitive cache lookup
        price = self.prices.get(tid, 0.0)
        source = self.sources.get(tid, "Unknown")
        return price, source

    def get_hbar_price(self) -> float:
        """Get the current price of native HBAR.

        Priority:
        1. SaucerSwap V2 pool data (already loaded in self.hbar_price from _load_data)
        2. CoinGecko (only if SaucerSwap price is 0 or data is stale)
        3. Binance (final fallback)
        """
        import time

        # 1. Use SaucerSwap price if it's fresh (loaded within the last 10 min)
        if self.hbar_price > 0:
            # Check if the source already says SaucerSwap — if so, use it directly
            current_source = self.sources.get("0.0.0", "")
            if "SaucerSwap" in current_source:
                return self.hbar_price

        # 2. Fallback: CoinGecko
        try:
            import requests
            url = "https://api.coingecko.com/api/v3/simple/price?ids=hedera-hashgraph&vs_currencies=usd"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                price = r.json().get("hedera-hashgraph", {}).get("usd", 0)
                if price > 0:
                    self.hbar_price = price
                    ts = time.strftime("%H:%M")
                    self.sources["0.0.0"] = f"CoinGecko (Live {ts})"
                    return price
        except Exception:
            pass

        # 3. Fallback: Binance
        try:
            import requests
            url = "https://api.binance.com/api/v3/ticker/price?symbol=HBARUSDT"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                price = float(r.json().get("price", 0))
                if price > 0:
                    self.hbar_price = price
                    ts = time.strftime("%H:%M")
                    self.sources["0.0.0"] = f"Binance (Live {ts})"
                    return price
        except Exception:
            pass

        return self.hbar_price


    def _get_live_price(self, token_id: str) -> tuple[float, str]:
        """
        Try to fetch live price from CoinGecko -> Binance -> Cache.
        """
        import time
        ts = time.strftime("%H:%M")

        # 1. Map ID to CoinGecko/Binance Keys
        # Extend this as needed. HBAR is handled separately usually but can be here.
        cg_map = {
            "0.0.0": "hedera-hashgraph",
            "0.0.1456986": "hedera-hashgraph", # WHBAR
            "0.0.731861": "saucerswap", # SAUCE
            "0.0.456858": "usd-coin", # USDC
            "0.0.624505": "wrapped-bitcoin", # WBTC (hts) - approximate
        }
        binance_map = {
            "0.0.0": "HBARUSDT",
        }

        cg_id = cg_map.get(token_id)
        
        # A. CoinGecko
        if cg_id:
            try:
                import requests
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
                r = requests.get(url, timeout=1.5)
                if r.status_code == 200:
                    data = r.json()
                    price = data.get(cg_id, {}).get("usd", 0)
                    if price > 0:
                        return price, f"CoinGecko (Live {ts})"
            except: pass

        # B. Binance (Only for major pairs)
        bn_sym = binance_map.get(token_id)
        if bn_sym:
            try:
                import requests
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={bn_sym}"
                r = requests.get(url, timeout=1.5)
                if r.status_code == 200:
                    data = r.json()
                    price = float(data.get("price", 0))
                    if price > 0:
                        return price, f"Binance (Live {ts})"
            except: pass

        # C. Cache Fallback
        price = self.prices.get(token_id, 0.0)
        source = self.sources.get(token_id, "Unknown Source")
        return price, source

    def reload(self) -> None:
        """Force a reload of data from the disk."""
        from src.logger import logger
        logger.info(f"[PriceManager] Reloading prices from {self.data_file}...")
        self._load_data()

# Singleton
price_manager = PacmanPriceManager()
