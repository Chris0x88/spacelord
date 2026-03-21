#!/usr/bin/env python3
"""
Refresh Data Script
===================

```python
Downloads all V2 pool data and necessary V1 pool data from the SaucerSwap API.
```
Saves everything — no manual whitelist filtering.
Auto-populates tokens.json with every token that has a V2 pool.
Marks preferred/default pools for ambiguous tokens (e.g. BTC, ETH).
"""

import json
import requests
import sys
import os
import time
from pathlib import Path

class C:
    R = "\033[0m"
    WARN = "\033[93m"
    OK = "\033[92m"
    BOLD = "\033[1m"

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data/"
DATA_DIR.mkdir(exist_ok=True)

import sys
sys.path.insert(0, str(ROOT_DIR))

from src.logger import logger

POOLS_URL_V2 = "https://api.saucerswap.finance/v2/pools"
POOLS_URL_V1 = "https://api.saucerswap.finance/pools"
RAW_DATA_FILE = DATA_DIR / "pacman_data_raw.json"
TOKENS_FILE   = DATA_DIR / "tokens.json"
POOLS_FILE    = DATA_DIR / "pools_v2.json"

PUBLIC_DEMO_KEY = "875e1017-87b8-4b12-8301-6aa1f1aa073b"

# ---------------------------------------------------------------------------
# Canonical token preferences.
# When a concept (e.g. "bitcoin") resolves to multiple token IDs, the one
# listed here is the DEFAULT — highest liquidity, most reliable V2 pool.
# ---------------------------------------------------------------------------
PREFERENCES = {
    # Bitcoin — HTS-WBTC has deepest V2 liquidity (0.0.10082597)
    "bitcoin": "0.0.10082597",
    "btc":     "0.0.10082597",
    "wbtc":    "0.0.10082597",
    # Ethereum — HTS-WETH (0.0.9770617)
    "ethereum": "0.0.9770617",
    "eth":      "0.0.9770617",
    "weth":     "0.0.9770617",
    # Stablecoins
    "usd":   "0.0.456858",
    "usdc":  "0.0.456858",
    "dollar": "0.0.456858",
    # Hedera
    "hbar":   "0.0.0",
    "hedera": "0.0.0",
}

# Human-readable aliases to inject into tokens.json so NLP resolves them correctly
ALIASES = {
    # These keys will be added to tokens.json pointing to the preferred token
    "BITCOIN":   "0.0.10082597",   # HTS-WBTC (highest V2 liquidity)
    "BTC":       "0.0.10082597",
    "WBTC_HTS":  "0.0.10082597",   # System canonical
    "ETHEREUM":  "0.0.9770617",    # HTS-WETH
    "ETH":       "0.0.9770617",
    "WETH_HTS":  "0.0.9770617",    # System canonical
    "DOLLAR":    "0.0.456858",
    "USD":       "0.0.456858",
    "HEDERA":    "0.0.0",
}

def load_env():
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value

def get_api_key():
    network = os.getenv("PACMAN_NETWORK", "mainnet").lower()
    if network == "testnet":
        key = os.getenv("SAUCERSWAP_API_KEY_TESTNET")
    else:
        key = os.getenv("SAUCERSWAP_API_KEY_MAINNET")
    if not key:
        key = PUBLIC_DEMO_KEY
        logger.info("[Refresh] Using public demo API key")
    return key

def fetch_url(url, api_key, label=""):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "x-api-key": api_key,
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
        logger.warning(f"[Refresh] {label} HTTP {r.status_code}")
    except Exception as e:
        logger.warning(f"[Refresh] {label} request failed: {e}")
    return None

def refresh(force=False):
    load_env()
    api_key = get_api_key()

    # Rate-limit: skip if data is < 60s old (unless forced)
    if not force and RAW_DATA_FILE.exists():
        age = time.time() - RAW_DATA_FILE.stat().st_mtime
        if age < 60:
            import sys as _sys
            print(f"  Using cached pool data ({int(age)}s old).", file=_sys.stderr)
            return

    print(f"{C.BOLD}📡 Fetching all V2 pools from SaucerSwap...{C.R}")

    # -------------------------------------------------------------------
    # 1. Fetch ALL V2 pools — no whitelist filter
    # -------------------------------------------------------------------
    v2_pools = fetch_url(POOLS_URL_V2, api_key, "V2") or []
    v1_all = fetch_url(POOLS_URL_V1, api_key, "V1") or []

    # 1.5 Filter V1 pools against the approved registry
    v1_pools = []
    try:
        approved_path = ROOT_DIR / "data/pools_v1.json"
        if approved_path.exists():
            with open(approved_path) as f:
                approved = json.load(f)
                approved_ids = {p["contractId"] for p in approved if "contractId" in p}
                v1_pools = [p for p in v1_all if p.get("contractId") in approved_ids]
    except Exception as e:
        print(f"  {C.WARN}⚠  Failed to load V1 approved list: {e}{C.R}")

    if not v2_pools:
        print(f"  {C.WARN}⚠  Failed to fetch V2 pools — using existing cache.{C.R}")
        return

    print(f"  {C.OK}✓{C.R}  Fetched {len(v2_pools)} V2 pools, {len(v1_pools)} V1 (approved) pools")

    # Tag each pool with its protocol so the router can distinguish
    for p in v2_pools:
        p.setdefault("protocol", "v2")
    for p in v1_pools:
        p.setdefault("protocol", "v1")

    all_pools = v2_pools + v1_pools
    # -------------------------------------------------------------------
    # 2. Update pools_v2.json: add any new pools (never remove existing)
    # -------------------------------------------------------------------
    existing_pools = []
    if POOLS_FILE.exists():
        with open(POOLS_FILE) as f:
            existing_pools = json.load(f)

    existing_pool_ids = {p.get("contractId") for p in existing_pools}
    new_pool_count = 0
    for p in all_pools:
        cid = p.get("contractId")
        if cid and cid not in existing_pool_ids:
            # Standardize minimal registry format
            ta = p.get("tokenA", {})
            tb = p.get("tokenB", {})
            ta_id = ta.get("id") if isinstance(ta, dict) else ta
            tb_id = tb.get("id") if isinstance(tb, dict) else tb
            
            reg_entry = {
                "contractId": cid,
                "tokenA": ta_id,
                "tokenB": tb_id,
                "fee": p.get("fee", 3000),
                "protocol": p.get("protocol", "v2")
            }
            existing_pools.append(reg_entry)
            existing_pool_ids.add(cid)
            new_pool_count += 1

    with open(POOLS_FILE, "w") as f:
        json.dump(existing_pools, f, indent=2)
    print(f"  {C.OK}✓{C.R}  pools_v2.json: {new_pool_count} new pools added ({len(existing_pools)} total)")

    # -------------------------------------------------------------------
    # 3. Save raw data (V2 + V1) — router uses this for pricing
    # -------------------------------------------------------------------
    with open(RAW_DATA_FILE, "w") as f:
        json.dump(all_pools, f, indent=2)
    print(f"  {C.OK}✓{C.R}  pacman_data_raw.json updated ({len(all_pools)} pools)")

    # -------------------------------------------------------------------
    # 4. Auto-populate tokens.json — V2 ONLY
    # V1 pools are not indexed: they contain many unvetted/scam tokens.
    # The existing tokens.json is the user-verified safe list.
    # Only V2 tokens (which have higher listing bar) are auto-added.
    # -------------------------------------------------------------------
    tokens = {}
    if TOKENS_FILE.exists():
        try:
            with open(TOKENS_FILE) as f:
                tokens = json.load(f)
        except Exception as e:
            print(f"  {C.WARN}⚠  Failed to load existing tokens.json: {e}{C.R}")

    existing_ids = {meta.get("id") for meta in tokens.values()}
    added_tokens = 0

    for pool in v2_pools:   # ← V2 only, never v1_pools
        for side in ["tokenA", "tokenB"]:
            t = pool.get(side)
            if not isinstance(t, dict):
                continue
            tid = t.get("id")
            if not tid or tid in existing_ids:
                continue

            sym = (t.get("symbol") or "UNKNOWN").strip()
            name = (t.get("name") or sym).strip()
            decimals = t.get("decimals", 8)

            # Build a unique registry key — avoid collisions
            key = sym.upper()
            if key in tokens:
                # Disambiguate by appending token num
                key = f"{sym.upper()}_{tid.split('.')[-1]}"

            tokens[key] = {
                "id": tid,
                "decimals": decimals,
                "symbol": sym,
                "name": name,
                "icon": t.get("icon", ""),
            }
            existing_ids.add(tid)
            added_tokens += 1


    # -------------------------------------------------------------------
    # 5. Inject NLP aliases (BITCOIN → WBTC_HTS, ETH → WETH_HTS, etc.)
    # -------------------------------------------------------------------
    # Load existing tokens to find metadata for preferred IDs
    id_to_meta = {meta.get("id"): meta for meta in tokens.values() if meta.get("id")}

    for alias_key, preferred_id in ALIASES.items():
        # Always override — alias keys MUST point to the preferred token.
        # Some low-value tokens have names like "BITCOIN" or "BTC" which would
        # otherwise hijack these keys. Preferred tokens win.
        meta = id_to_meta.get(preferred_id)
        if meta:
            tokens[alias_key] = {
                "id": preferred_id,
                "decimals": meta.get("decimals", 8),
                "symbol": meta.get("symbol", alias_key),
                "name": meta.get("name", alias_key),
                "alias_for": preferred_id,
                "preferred": True,
            }
        else:
            tokens[alias_key] = {
                "id": preferred_id,
                "decimals": 8,
                "symbol": alias_key,
                "name": alias_key,
                "alias_for": preferred_id,
                "preferred": True,
            }

    # -------------------------------------------------------------------
    # 6. Mark preferred variants (for ambiguous tokens)
    # -------------------------------------------------------------------
    # Find all tokens that share an underlying asset and tag the preferred one
    concept_map = {}  # concept_name -> preferred_id
    for concept, pid in PREFERENCES.items():
        concept_map[pid] = concept

    for key, meta in tokens.items():
        tid = meta.get("id")
        if tid in concept_map:
            meta["preferred"] = True  # e.g. "This is the preferred WBTC"
        elif "preferred" in meta:
            del meta["preferred"]

    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

    print(f"  {C.OK}✓{C.R}  tokens.json: {added_tokens} new tokens added ({len(tokens)} total)")
    print(f"  {C.OK}✓{C.R}  NLP aliases injected: {', '.join(ALIASES.keys())}")
    print(f"\n{C.OK}✅ Refresh complete.{C.R}")

if __name__ == "__main__":
    force = "--force" in sys.argv
    refresh(force=force)
