"""
Hedera Ecosystem Token Price History
=====================================

Fetches and caches daily price data for Hedera ecosystem tokens
(HBAR, SAUCE, HBARX, etc.) from SaucerSwap and public APIs.

Data strategy: download history once from CoinGecko, then append
daily updates. Cache stored in data/hedera_prices_1d.json.
"""

import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from src.logger import logger

CACHE_PATH = Path("data/hedera_prices_1d.json")

# CoinGecko IDs for Hedera ecosystem tokens
# Free API: max 365 days history, rate limited (10-30 req/min)
COINGECKO_TOKENS = {
    "HBAR": "hedera-hashgraph",
    "SAUCE": "saucerswap",
}

# SaucerSwap token IDs for on-chain price lookups (fallback/supplement)
SAUCERSWAP_TOKENS = {
    "HBAR": "0.0.0",
    "SAUCE": "0.0.731861",
    "WBTC": "0.0.10082597",
    "WETH": "0.0.9770617",
    "USDC": "0.0.456858",
}


def get_hedera_price_history(days: int = 365) -> dict:
    """
    Get daily price history for Hedera ecosystem tokens.

    Returns dict: { "HBAR": [{"date": "2024-03-18", "price": 0.107}, ...], ... }

    Strategy:
    1. Load cache
    2. For each token, check if data is stale (> 12 hours old)
    3. If stale, fetch missing days from CoinGecko
    4. Merge and save cache
    """
    cache = _load_cache()
    updated = False
    now = datetime.utcnow()

    for symbol, cg_id in COINGECKO_TOKENS.items():
        token_data = cache.get(symbol, {"prices": [], "last_fetch": None})
        prices = token_data.get("prices", [])
        last_fetch = token_data.get("last_fetch")

        # Check if we need to update
        stale = True
        if last_fetch:
            try:
                last_dt = datetime.fromisoformat(last_fetch)
                stale = (now - last_dt).total_seconds() > 43200  # 12 hours
            except Exception:
                pass

        if not stale and len(prices) > 30:
            continue  # Cache is fresh enough

        # Determine how many days to fetch
        if prices:
            # Find the last date in cache
            last_date_str = prices[-1].get("date", "")
            try:
                last_cached = datetime.strptime(last_date_str, "%Y-%m-%d")
                fetch_days = max(7, (now - last_cached).days + 1)
            except Exception:
                fetch_days = days
        else:
            fetch_days = days

        # Fetch from CoinGecko
        new_prices = _fetch_coingecko(cg_id, fetch_days)
        if new_prices:
            # Merge: keep existing, add/overwrite with new
            existing_map = {p["date"]: p["price"] for p in prices}
            for p in new_prices:
                existing_map[p["date"]] = p["price"]

            # Sort by date
            merged = [{"date": d, "price": p} for d, p in sorted(existing_map.items())]
            cache[symbol] = {
                "prices": merged,
                "last_fetch": now.isoformat(),
                "source": "coingecko",
            }
            updated = True
            logger.info(f"[HederaChart] Updated {symbol}: {len(merged)} data points")
            time.sleep(1.5)  # Rate limit: CoinGecko free tier

    if updated:
        _save_cache(cache)

    # Return just the price arrays
    return {sym: data.get("prices", []) for sym, data in cache.items()}


def _fetch_coingecko(coin_id: str, days: int) -> list:
    """Fetch daily price history from CoinGecko free API."""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": min(days, 365), "interval": "daily"}
        resp = requests.get(url, params=params, timeout=15)

        if resp.status_code == 429:
            logger.warning(f"[HederaChart] CoinGecko rate limited for {coin_id}")
            return []
        if resp.status_code != 200:
            logger.warning(f"[HederaChart] CoinGecko {resp.status_code} for {coin_id}")
            return []

        data = resp.json()
        prices = data.get("prices", [])

        result = []
        for ts_ms, price in prices:
            dt = datetime.utcfromtimestamp(ts_ms / 1000)
            result.append({
                "date": dt.strftime("%Y-%m-%d"),
                "price": round(price, 8),
            })

        return result
    except Exception as e:
        logger.error(f"[HederaChart] CoinGecko fetch error for {coin_id}: {e}")
        return []


def _load_cache() -> dict:
    """Load price cache from disk."""
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[HederaChart] Cache load error: {e}")
    return {}


def _save_cache(cache: dict):
    """Save price cache to disk."""
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.error(f"[HederaChart] Cache save error: {e}")
