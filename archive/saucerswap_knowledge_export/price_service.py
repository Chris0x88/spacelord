import os
import asyncio
import httpx
import logging
import time
import copy
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

# Canonical IDs for high-frequency sync
WBTC_ID = "0.0.10082597"
USDC_ID = "0.0.456858"
USDC_HTS_ID = "0.0.1055459"
WHBAR_ID = "0.0.1456986"
WETH_ID = "0.0.9770617"

# Registry path
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "token_registry.json"

class DataRegistry:
    """
    Centralized In-Memory Data Store.
    Only source of truth for the API and Router during runtime.
    Updated by the background_data_sync task.
    
    UNIFIED TOKEN ID SYSTEM:
    - Primary key: hedera_id (e.g., "0.0.10082597")
    - Symbol aliases maintained for backward compatibility
    """
    def __init__(self):
        self.prices = {}  # hedera_id -> price (primary index)
        self.sources = {}  # hedera_id -> source string
        self.pool_info = {}  # pool_address -> tvl_usd
        self.pools = {}  # hedera_id -> pool_data for UI
        self.last_updated = None
        self.lock = asyncio.Lock()
        # Symbol -> hedera_id mapping for backward compatibility
        self._symbol_to_id = {}

    async def update(self, prices: Dict[str, float] = None, sources: Dict[str, str] = None, 
                     pool_info: Dict[str, float] = None, pools: Dict[str, Any] = None,
                     symbol_map: Dict[str, str] = None):
        async with self.lock:
            if prices:
                # Keys are now hedera_ids (0.0.x format) - store as-is
                self.prices.update(prices)
            if sources:
                self.sources.update(sources)
            if pool_info:
                self.pool_info.update(pool_info)
            if pools:
                self.pools.update(pools)
            if symbol_map:
                # Update symbol -> hedera_id mapping
                self._symbol_to_id.update({k.upper(): v for k, v in symbol_map.items()})
            self.last_updated = datetime.now(timezone.utc)

    def get_price(self, key: str) -> Optional[float]:
        """
        Get price by hedera_id or symbol (sync method for convenience).
        Tries hedera_id first, then symbol lookup.
        """
        # Direct hedera_id lookup
        if key in self.prices:
            return self.prices[key]
        # Symbol lookup via mapping
        key_upper = key.upper()
        if key_upper in self._symbol_to_id:
            hid = self._symbol_to_id[key_upper]
            return self.prices.get(hid)
        # Legacy: try uppercase key directly (for backward compat during migration)
        return self.prices.get(key_upper)

    async def get_all(self):
        async with self.lock:
            return copy.deepcopy(self.prices), copy.deepcopy(self.sources), copy.deepcopy(self.pool_info), self.last_updated, copy.deepcopy(self.pools)
    
    async def get_symbol_map(self) -> Dict[str, str]:
        """Get the symbol -> hedera_id mapping."""
        async with self.lock:
            return copy.deepcopy(self._symbol_to_id)

# Shared registry instance
price_cache = DataRegistry()
price_refresh_lock = asyncio.Lock()

def get_price_registry() -> DataRegistry:
    """Get the centralized data registry singleton."""
    return price_cache

async def fetch_saucerswap_data(endpoint: str) -> Optional[Any]:
    """Helper to fetch from SaucerSwap REST API with auth."""
    key = os.environ.get("SAUCERSWAP_API_KEY")
    headers = {"x-api-key": key} if key else {}
    url = f"https://api.saucerswap.finance{endpoint}"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return res.json()
            if res.status_code == 401:
                logger.error(f"[Sync] SaucerSwap API Unauthorized (401). Check SAUCERSWAP_API_KEY.")
            else:
                logger.error(f"[Sync] SaucerSwap API error {res.status_code} on {endpoint}")
        except Exception as e:
            logger.error(f"[Sync] SaucerSwap fetch failed on {endpoint}: {e}")
    return None

async def sync_fast_prices():
    """1s Sync: Fetch all whitelisted token prices from SaucerSwap.
    
    UNIFIED TOKEN ID SYSTEM: Indexes prices by hedera_id (0.0.x format).
    """
    tokens = await fetch_saucerswap_data("/tokens")
    if not tokens:
        logger.debug("[Sync] Fast sync: No tokens returned from SaucerSwap API")
        return
    
    try:
        from robot.token_whitelist import WHITELIST
    except ImportError:
        from token_whitelist import WHITELIST

    new_prices = {}
    new_sources = {}
    symbol_map = {}  # symbol -> hedera_id for backward compatibility
    
    # Map fetched token IDs to prices
    id_to_price = {t['id']: float(t.get('priceUsd', 0)) for t in tokens if t.get('priceUsd')}
    
    # Update all whitelisted tokens - index by hedera_id
    for symbol, token in WHITELIST.items():
        hid = token.hedera_id
        if hid in id_to_price:
            price = id_to_price[hid]
            source = "SaucerSwap"
            # Primary index: hedera_id
            new_prices[hid] = price
            new_sources[hid] = source
            # Build symbol -> hedera_id mapping
            symbol_map[symbol.upper()] = hid
            # Also map saucer_symbol if different
            if hasattr(token, 'saucer_symbol') and token.saucer_symbol:
                symbol_map[token.saucer_symbol.upper()] = hid
    
    # --- Bi-directional Price Piggybacking ---
    try:
        from robot.tokens import TokenID
    except ImportError:
        from tokens import TokenID

    # Ensure HBAR and variants share prices if one is missing (Source of Truth: TokenID)
    piggybacks = [
        (TokenID.WBTC_L0, TokenID.WBTC_HTS),
        (TokenID.WETH_L0, TokenID.WETH_HTS),
        (TokenID.WHBAR, TokenID.HBAR)
    ]
    for canonical_id, variant_id in piggybacks:
        # Variant inherits from Canonical
        if canonical_id in new_prices and (variant_id not in new_prices or new_prices[variant_id] <= 0):
            new_prices[variant_id] = new_prices[canonical_id]
            new_sources[variant_id] = f"Piggyback({new_sources.get(canonical_id, 'Unknown')})"
        # Canonical inherits from Variant (backup)
        elif variant_id in new_prices and (canonical_id not in new_prices or new_prices[canonical_id] <= 0):
            new_prices[canonical_id] = new_prices[variant_id]
            new_sources[canonical_id] = f"Piggyback({new_sources.get(variant_id, 'Unknown')})"
            
    if new_prices:
        await price_cache.update(prices=new_prices, sources=new_sources, symbol_map=symbol_map)
        logger.debug(f"[Sync] Fast sync updated {len(new_prices)} prices (indexed by hedera_id)")
    else:
        logger.warning(f"[Sync] Fast sync: No prices matched whitelist tokens.")

async def sync_pool_depths():
    """3s Sync: Fetch high-priority pool TVLs.
    
    UNIFIED TOKEN ID SYSTEM: Indexes pools by hedera_id (0.0.x format).
    """
    pools_data = await fetch_saucerswap_data("/v2/pools")
    if not pools_data: return
    
    new_pool_info = {}
    new_pools_ui = {}  # hedera_id -> {pool_address, fee_tier, tvl}
    # target_ids = {WBTC_ID, USDC_ID, USDC_HTS_ID, WHBAR_ID}
    
    # Better: update any pool where BOTH tokens are in our registry
    try:
        from robot.approved_pool_router import get_router
    except ImportError:
        from approved_pool_router import get_router
    router = get_router()
    registry_ids = set(router.id_map.keys())
    
    for p in pools_data:
        tA = p.get('tokenA', {}).get('id')
        tB = p.get('tokenB', {}).get('id')
        addr = p.get('contractId')
        fee = p.get('fee')
        if not addr: continue
        
        # Check if it's one of our registered tokens
        if tA in registry_ids and tB in registry_ids:
            tvl = 0
            try:
                tvl = float(p.get('tvlUsd', 0))
                # TVL calculation fallback
                if tvl <= 0:
                    prA = float(p.get('tokenA', {}).get('priceUsd', 0))
                    prB = float(p.get('tokenB', {}).get('priceUsd', 0))
                    amtA = float(p.get('amountA', 0)) / (10**int(p.get('tokenA', {}).get('decimals', 8)))
                    amtB = float(p.get('amountB', 0)) / (10**int(p.get('tokenB', {}).get('decimals', 6)))
                    tvl = (amtA * prA) + (amtB * prB)
            except: pass
            
            if tvl > 0:
                new_pool_info[addr] = tvl
                # Update UI map for tokens in this pool - index by hedera_id
                for tid in [tA, tB]:
                    # Prefer largest pool for UI display
                    if tid not in new_pools_ui or tvl > new_pools_ui[tid].get('tvl', 0):
                        new_pools_ui[tid] = {
                            "pool_address": addr,
                            "fee_tier": fee,
                            "tvl": tvl
                        }
                
                # Push update directly to the router's in-memory graph
                try:
                    router.update_pool_tvl(addr, tvl)
                except Exception as e:
                    logger.debug(f"[Sync] Router update failed: {e}")
                
    if new_pool_info:
        await price_cache.update(pool_info=new_pool_info, pools=new_pools_ui)

async def refresh_all_prices(priority_only: bool = False):
    """60s Sync: Full refresh of all whitelisted assets.
    
    UNIFIED TOKEN ID SYSTEM: Indexes prices by hedera_id (0.0.x format).
    """
    tokens = await fetch_saucerswap_data("/tokens")
    if not tokens:
        logger.warning("[Sync] Full refresh: No tokens returned from SaucerSwap API")
        return {}, {}, {}
    
    try:
        from robot.token_whitelist import WHITELIST
    except ImportError:
        from token_whitelist import WHITELIST
        
    id_to_price = {t['id']: float(t.get('priceUsd', 0)) for t in tokens if t.get('priceUsd')}
    logger.debug(f"[Sync] Full refresh: Found {len(id_to_price)} prices from SaucerSwap API")
    
    new_prices = {}
    new_sources = {}
    symbol_map = {}  # symbol -> hedera_id for backward compatibility
    
    for symbol, token in WHITELIST.items():
        hid = token.hedera_id
        if hid in id_to_price:
            price = id_to_price[hid]
            if price > 0:
                # Primary index: hedera_id
                new_prices[hid] = price
                new_sources[hid] = "SaucerSwap"
                # Build symbol -> hedera_id mapping
                symbol_map[symbol.upper()] = hid
                # Also map saucer_symbol if different
                if hasattr(token, 'saucer_symbol') and token.saucer_symbol:
                    symbol_map[token.saucer_symbol.upper()] = hid
                
    if new_prices:
        await price_cache.update(prices=new_prices, sources=new_sources, symbol_map=symbol_map)
        logger.info(f"[Sync] Full refresh updated {len(new_prices)} prices (indexed by hedera_id)")
    else:
        logger.warning(f"[Sync] Full refresh: No prices matched whitelist. Found {len(id_to_price)} prices in API response")
    
    return new_prices, new_sources, {}

async def persist_registry_to_disk():
    """Persist current memory state back to robot/token_registry.json."""
    if not REGISTRY_PATH.exists(): return
    
    prices, _, pool_info, _, _ = await price_cache.get_all()
    
    try:
        with open(REGISTRY_PATH, "r") as f:
            registry = json.load(f)
            
        changed = False
        for token in registry:
            for pool in token.get('pools', []):
                addr = pool.get('pool_address')
                if addr in pool_info:
                    # Update TVL if it differs by more than $1
                    if abs(pool.get('tvl_usd', 0) - pool_info[addr]) > 1.0:
                        pool['tvl_usd'] = pool_info[addr]
                        pool['last_sync'] = datetime.now(timezone.utc).isoformat()
                        changed = True
                    
        if changed:
            with open(REGISTRY_PATH, "w") as f:
                json.dump(registry, f, indent=4)
            logger.info(f"[Sync] Registry persistence: Updated TVLs for matched pools.")
    except Exception as e:
        logger.error(f"[Sync] Persistence failed: {e}")

async def fetch_coingecko_prices(ids: List[str]) -> Dict[str, float]:
    """Fetches prices from CoinGecko (no API key required for small loads)."""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": ",".join(ids), "vs_currencies": "usd"},
                timeout=5.0
            )
            if res.status_code == 200:
                data = res.json()
                return {gc_id: float(price_data.get("usd", 0)) for gc_id, price_data in data.items()}
            else:
                logger.warning(f"[CoinGecko] API error: {res.status_code}")
    except Exception as e:
        logger.warning(f"[CoinGecko] Price fetch failed: {e}")
    return {}


async def fetch_binance_btc_data() -> Tuple[float, float]:
    """Fetches BTC price and 24h change from Binance."""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                price = float(data.get("lastPrice", 0))
                change = float(data.get("priceChangePercent", 0.0))
                if price > 0:
                    return price, change
                else:
                    logger.warning("[Binance] Invalid price returned: 0")
            else:
                logger.warning(f"[Binance] API error: {res.status_code}")
    except httpx.TimeoutException:
        logger.warning("[Binance] Request timeout")
    except Exception as e:
        logger.warning(f"[Binance] Fetch error: {e}")
    return 0.0, 0.0


async def background_data_sync():
    """Main background loop orchestrating the high-frequency sync."""
    logger.info("[Background] Starting High-Frequency Centralized Data Sync task...")
    
    # Initial full load
    try:
        logger.info("[Background] Running initial price refresh...")
        await refresh_all_prices()
        await sync_pool_depths()
        # Verify cache was populated
        prices, sources, _, _, _ = await price_cache.get_all()
        logger.info(f"[Background] Initial cache populated: {len(prices)} prices, sources: {list(sources.values())[:3] if sources else 'empty'}")
    except Exception as e:
        logger.error(f"[Background] Initial load failed: {e}")
        import traceback
        traceback.print_exc()
    
    count_1s = 0
    while True:
        try:
            # 1. High-Frequency Prices (1s)
            await sync_fast_prices()
            
            # Fetch Binance BTC data separately for research data
            try:
                binance_btc, binance_change = await fetch_binance_btc_data()
                if binance_btc:
                    await price_cache.update(
                        prices={'BTC_BINANCE': binance_btc, 'BTC_BINANCE_CHANGE': binance_change},
                        sources={'BTC_BINANCE': 'Binance', 'BTC_BINANCE_CHANGE': 'Binance'}
                    )
            except Exception as e:
                logger.warning(f"[Background] Binance BTC fetch failed: {e}")
            
            # 2. Medium-Frequency Pools (3s)
            if count_1s % 3 == 0:
                await sync_pool_depths()
                
            # 3. Low-Frequency Full Refresh & Persistence (60s)
            if count_1s % 60 == 0:
                await refresh_all_prices()
                await persist_registry_to_disk()
                
                # Fetch EVM prices for valuation
                try:
                    cg_prices = await fetch_coingecko_prices(["ethereum", "matic-network", "bitcoin", "usd-coin"])
                    if cg_prices:
                        await price_cache.update(
                            prices={f"CG_{k.upper()}": v for k, v in cg_prices.items()},
                            sources={f"CG_{k.upper()}": "CoinGecko" for k in cg_prices.keys()}
                        )
                except Exception as e:
                    logger.warning(f"[Background] CG fetch failed: {e}")

                # Log cache state every 60s
                prices, sources, _, _, _ = await price_cache.get_all()
                logger.info(f"[Background] 60s refresh complete: {len(prices)} prices in cache")
                
            count_1s = (count_1s + 1) % 3600
        except Exception as e:
            logger.error(f"[Background] Data Sync loop encountered an error: {e}")
            import traceback
            traceback.print_exc()
            
        await asyncio.sleep(1)

# Aliases for backward compatibility
background_price_refresh = background_data_sync

async def fetch_binance_btc_price() -> float:
    """Fallback only: fetches BTC price from Binance."""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=2.0)
            if res.status_code == 200:
                return float(res.json().get("price", 0.0))
    except: pass
    return 0.0
