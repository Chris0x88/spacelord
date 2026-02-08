#!/usr/bin/env python3
"""
Route Table Builder
===================

Reads pacman_data_raw.json (SaucerSwap V2 pool snapshot) and pre-computes
the optimal swap route for every tradeable token pair.

Output: routes.json - a flat lookup table the agent uses at runtime.

Run this weekly (or whenever new tokens/pools appear):
    python3 build_routes.py
"""

import json
from pathlib import Path
from itertools import combinations

POOLS_FILE = Path(__file__).parent / "pacman_data_raw.json"
OUTPUT_FILE = Path(__file__).parent / "routes.json"
TOKENS_FILE = Path(__file__).parent / "tokens.json"

# WHBAR is 0.0.1456986. It is a technical wrapper, NOT a tradeable asset.
WHBAR_ID = "0.0.1456986"

# Preferred canonical names for core tokens to maintain backward compatibility
# and ensure clean, predictable naming.
PREFERRED_NAMES = {
    "0.0.456858":   "USDC",
    "0.0.1055459":  "USDC_HTS",
    "0.0.1055472":  "USDT_HTS",
    "0.0.1055477":  "DAI_HTS",
    "0.0.10082597": "WBTC_HTS",
    "0.0.1055483":  "WBTC_LZ",
    "0.0.541564":   "WETH_HTS",
    "0.0.9770617":  "WETH_LZ",
    "0.0.731861":   "SAUCE",
    "0.0.1460200":  "XSAUCE",
}

def discover_tokens(raw_pools):
    """
    Scan pool data to build a comprehensive token registry.
    Only includes tokens found in pools with TVL >= $10,000 USD.
    Returns: { canonical_name: {id, decimals, symbol, name, priceUsd} }
    """
    registry = {}
    id_to_canonical = {}
    
    # helper to check if a token is in a high-liquidity pool
    valid_token_ids = set(PREFERRED_NAMES.keys())
    
    # Pass 0: Find all tokens in high-liquidity pools
    for pool in raw_pools:
        # TVL calculation
        tA = pool["tokenA"]
        tB = pool["tokenB"]
        pA = tA.get("priceUsd", 0)
        pB = tB.get("priceUsd", 0)
        
        # amountA/B are strings often representing big integers. 
        # MUST divide by 10**decimals BEFORE multiplying by price.
        valA = (float(pool["amountA"]) / (10**tA["decimals"])) * pA
        valB = (float(pool["amountB"]) / (10**tB["decimals"])) * pB
        tvl = valA + valB
              
        # Ignore pools with no liquidity data
        if int(pool.get("liquidity", "0")) == 0:
            continue
            
        if tvl >= 10000 or tA["id"] in PREFERRED_NAMES or tB["id"] in PREFERRED_NAMES:
            valid_token_ids.add(tA["id"])
            valid_token_ids.add(tB["id"])
        elif tA["symbol"].lower() == "stickbug" or tB["symbol"].lower() == "stickbug":
             # This will help me see why it's still being kept if it somehow is
             pass

    # Pass 1: Handle preferred names first (if they are valid)
    for tid in PREFERRED_NAMES:
        if tid in valid_token_ids:
            # We need to find the token info from ANY pool it's in
            for pool in raw_pools:
                for side in ["tokenA", "tokenB"]:
                    t = pool[side]
                    if t["id"] == tid and tid not in id_to_canonical:
                        canon = PREFERRED_NAMES[tid]
                        id_to_canonical[tid] = canon
                        registry[canon] = {
                            "id": tid,
                            "decimals": t["decimals"],
                            "symbol": t["symbol"],
                            "name": t["name"],
                            "priceUsd": t.get("priceUsd"),
                            "icon": t.get("icon")
                        }

    # Pass 2: Discover everything else that's valid
    for pool in raw_pools:
        for side in ["tokenA", "tokenB"]:
            t = pool[side]
            tid = t["id"]
            
            if tid == WHBAR_ID or tid not in valid_token_ids or tid in id_to_canonical:
                continue
                
            # Create a canonical name
            sym = t["symbol"].upper()
            base_sym = sym.replace("[HTS]", "_HTS").replace("-", "_").replace(" ", "_")
            
            unique_name = base_sym
            counter = 1
            while unique_name in registry:
                unique_name = f"{base_sym}_{counter}"
                counter += 1
            
            id_to_canonical[tid] = unique_name
            registry[unique_name] = {
                "id": tid,
                "decimals": t["decimals"],
                "symbol": t["symbol"],
                "name": t["name"],
                "priceUsd": t.get("priceUsd"),
                "icon": t.get("icon")
            }

    return registry, id_to_canonical

# Global state for IDs (populated during build)
_ID_TO_CANONICAL = {}
_ALL_TOKENS = {}

def load_pools():
    """Load raw pool data and build adjacency list."""
    with open(POOLS_FILE) as f:
        raw = json.load(f)

    # 1. Discover all tokens
    token_registry, id_to_canonical = discover_tokens(raw)
    
    # 2. Add WHBAR to the internal routing registry
    whbar_meta = {
        "id": WHBAR_ID,
        "decimals": 8,
        "symbol": "HBAR",
        "name": "WHBAR (routing only)",
        "priceUsd": None
    }
    
    global _ID_TO_CANONICAL, _ALL_TOKENS
    _ID_TO_CANONICAL = dict(id_to_canonical)
    _ID_TO_CANONICAL[WHBAR_ID] = "WHBAR"
    
    _ALL_TOKENS = dict(token_registry)
    _ALL_TOKENS["WHBAR"] = whbar_meta

    # adjacency: (canonical_a, canonical_b) -> {pool_id, fee, liquidity, ...}
    pools = {}
    for pool in raw:
        id_a = pool["tokenA"]["id"]
        id_b = pool["tokenB"]["id"]

        # Resolve to canonical names
        canon_a = _ID_TO_CANONICAL.get(id_a)
        canon_b = _ID_TO_CANONICAL.get(id_b)

        if not canon_a or not canon_b:
            continue

        # Quality Control: TVL-based Filtering
        # TVL = (amountA * priceUsdA) + (amountB * priceUsdB)
        # We only keep pools with TVL >= $10,000 USD to avoid "shitcoins"
        
        meta_a = _ALL_TOKENS.get(canon_a)
        meta_b = _ALL_TOKENS.get(canon_b)
        
        p_a = meta_a.get("priceUsd") if meta_a else None
        p_b = meta_b.get("priceUsd") if meta_b else None
        
        # Calculate TVL
        tvl = 0
        if p_a:
            tvl += (float(pool["amountA"]) / 10**meta_a["decimals"]) * p_a
        if p_b:
            tvl += (float(pool["amountB"]) / 10**meta_b["decimals"]) * p_b
            
        # Decision: Keep if TVL >= $10k OR if it's a core token pair
        is_core = id_a in PREFERRED_NAMES or id_b in PREFERRED_NAMES
        if tvl < 10000 and not is_core:
            continue

        pair = tuple(sorted([canon_a, canon_b]))
        fee = pool["fee"]
        liq = int(pool.get("liquidity", "0"))

        key = (pair, fee)
        if key not in pools or liq > pools[key]["liquidity"]:
            pools[key] = {
                "pool_id": pool["id"],
                "token_a": canon_a,
                "token_b": canon_b,
                "token_a_id": id_a,
                "token_b_id": id_b,
                "fee": fee,
                "liquidity": liq,
                "tvl": tvl
            }

    return list(pools.values()), token_registry


def build_adjacency(pools):
    """Build adjacency dict: token -> [(neighbor, pool_info)]."""
    adj = {}
    for p in pools:
        a, b = p["token_a"], p["token_b"]
        adj.setdefault(a, []).append((b, p))
        adj.setdefault(b, []).append((a, p))
    return adj


def find_top_routes(adj, src, dst, max_hops=3, top_n=3):
    """
    Find the top N candidate routes from src to dst.
    Score = sum of (fee / 1000000) for each hop + liquidity penalties.
    Returns a list of routes sorted by best score.
    """
    if src == dst:
        return []

    candidates = []
    # BFS with path tracking
    queue = [(src, [src], 0.0, [])]  # (current, path, cost, hops_info)

    while queue:
        current, path, cost, hops = queue.pop(0)

        if current == dst:
            route_obj = {
                "path": path,
                "hops": hops,
                "total_fee_percent": round(cost * 100, 4),
                "num_hops": len(hops),
                "score": cost
            }
            candidates.append(route_obj)
            continue

        if len(path) - 1 >= max_hops:
            continue

        for neighbor, pool_info in adj.get(current, []):
            if neighbor in path:
                continue  # no cycles

            hop_fee = pool_info["fee"] / 1_000_000
            # Liquidity penalty for thin pools
            liq_penalty = 0.0
            if pool_info["liquidity"] < 1_000_000:
                liq_penalty = 0.05
            elif pool_info["liquidity"] < 10_000_000:
                liq_penalty = 0.01

            hop_info = {
                "from": current,
                "to": neighbor,
                "pool_id": pool_info["pool_id"],
                "fee": pool_info["fee"],
                "fee_percent": round(pool_info["fee"] / 10000, 4),
                "token_in_id": _ALL_TOKENS[current]["id"],
                "token_out_id": _ALL_TOKENS[neighbor]["id"],
                "decimals_in": _ALL_TOKENS[current]["decimals"],
                "decimals_out": _ALL_TOKENS[neighbor]["decimals"],
                "liquidity": pool_info["liquidity"],
            }

            queue.append((
                neighbor,
                path + [neighbor],
                cost + hop_fee + liq_penalty,
                hops + [hop_info],
            ))

    # Sort by score and take top N
    candidates.sort(key=lambda x: x["score"])
    
    # Remove scores from output
    for c in candidates:
        del c["score"]
        
    return candidates[:top_n]


def build_route_table():
    """Build the complete route lookup table."""
    pools, token_registry = load_pools()
    adj = build_adjacency(pools)

    all_graph_tokens = sorted(adj.keys())
    # Tradeable tokens: exclude WHBAR
    tradeable = [t for t in all_graph_tokens if t != "WHBAR"]
    print(f"Building routes for {len(tradeable)} tradeable tokens "
          f"({len(all_graph_tokens)} in graph) across {len(pools)} pools...")

    routes = {}
    no_route = []

    for src in tradeable:
        for dst in tradeable:
            if src == dst:
                continue

            # Route finding uses full graph (WHBAR as hop is fine)
            candidates = find_top_routes(adj, src, dst)
            key = f"{src}->{dst}"

            if candidates:
                routes[key] = candidates
            else:
                no_route.append(key)

    # Build output - only tradeable tokens in the token list
    output = {
        "version": 2,
        "token_count": len(tradeable),
        "route_count": len(routes),
        "tokens": token_registry,
        "routes": routes,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    # Also save the token registry for the translator
    with open(TOKENS_FILE, "w") as f:
        json.dump(token_registry, f, indent=2)

    print(f"Wrote {len(routes)} routes to {OUTPUT_FILE}")
    print(f"Wrote {len(token_registry)} tokens to {TOKENS_FILE}")
    if no_route:
        print(f"No route found for {len(no_route)} pairs (disconnected tokens)")

    return output


if __name__ == "__main__":
    build_route_table()
