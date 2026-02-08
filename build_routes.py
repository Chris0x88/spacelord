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

# Canonical token registry
# Maps user-facing symbol -> hedera token ID + metadata
# The agent only speaks these names. Everything else is internal.
TOKEN_REGISTRY = {
    "USDC":       {"id": "0.0.456858",    "decimals": 6,  "symbol_on_pool": "USDC"},
    "USDC_HTS":   {"id": "0.0.1055459",   "decimals": 6,  "symbol_on_pool": "USDC[hts]"},
    "USDT_HTS":   {"id": "0.0.1055472",   "decimals": 6,  "symbol_on_pool": "USDT[hts]"},
    "DAI_HTS":    {"id": "0.0.1055477",   "decimals": 8,  "symbol_on_pool": "DAI[hts]"},
    "HBAR":       {"id": "0.0.1456986",   "decimals": 8,  "symbol_on_pool": "HBAR"},
    "WBTC_HTS":   {"id": "0.0.10082597",  "decimals": 8,  "symbol_on_pool": "HTS-WBTC"},
    "WBTC_LZ":    {"id": "0.0.1055483",   "decimals": 8,  "symbol_on_pool": "WBTC[hts]"},
    "WETH_HTS":   {"id": "0.0.541564",    "decimals": 8,  "symbol_on_pool": "WETH[hts]"},
    "WETH_LZ":    {"id": "0.0.9770617",   "decimals": 8,  "symbol_on_pool": "HTS-WETH"},
    "SAUCE":      {"id": "0.0.731861",    "decimals": 6,  "symbol_on_pool": "SAUCE"},
    "XSAUCE":     {"id": "0.0.1460200",   "decimals": 6,  "symbol_on_pool": "XSAUCE"},
    "HBARX":      {"id": "0.0.834116",    "decimals": 8,  "symbol_on_pool": "HBARX"},
    "KARATE":     {"id": "0.0.2283230",   "decimals": 8,  "symbol_on_pool": "KARATE"},
    "DOVU":       {"id": "0.0.3716059",   "decimals": 8,  "symbol_on_pool": "DOVU"},
    "PACK":       {"id": "0.0.4794920",   "decimals": 6,  "symbol_on_pool": "PACK"},
    "GRELF":      {"id": "0.0.1159074",   "decimals": 8,  "symbol_on_pool": "GRELF"},
    "LINK_HTS":   {"id": "0.0.1055495",   "decimals": 8,  "symbol_on_pool": "LINK[hts]"},
    "WAVAX_HTS":  {"id": "0.0.1157020",   "decimals": 8,  "symbol_on_pool": "WAVAX[hts]"},
    "QNT_HTS":    {"id": "0.0.1304757",   "decimals": 8,  "symbol_on_pool": "QNT[hts]"},
    "HCHF":       {"id": "0.0.6070123",   "decimals": 8,  "symbol_on_pool": "HCHF"},
    "HLQT":       {"id": "0.0.6070128",   "decimals": 8,  "symbol_on_pool": "HLQT"},
    "BONZO":      {"id": "0.0.8279134",   "decimals": 8,  "symbol_on_pool": "BONZO"},
    "HST":        {"id": "0.0.968069",    "decimals": 8,  "symbol_on_pool": "HST"},
    "CLXY":       {"id": "0.0.859814",    "decimals": 6,  "symbol_on_pool": "CLXY"},
    "WBNB_HTS":   {"id": "0.0.1157005",   "decimals": 8,  "symbol_on_pool": "WBNB[hts]"},
    "DAVINCI":    {"id": "0.0.3706639",   "decimals": 9,  "symbol_on_pool": "DAVINCI"},
    "CARAT":      {"id": "0.0.1958126",   "decimals": 2,  "symbol_on_pool": "CARAT"},
}

# Reverse: pool symbol -> canonical name
_POOL_SYMBOL_TO_CANONICAL = {}
for canon, meta in TOKEN_REGISTRY.items():
    _POOL_SYMBOL_TO_CANONICAL[meta["symbol_on_pool"]] = canon

# Also map token ID -> canonical name
_ID_TO_CANONICAL = {}
for canon, meta in TOKEN_REGISTRY.items():
    _ID_TO_CANONICAL[meta["id"]] = canon


def load_pools():
    """Load raw pool data and build adjacency list."""
    with open(POOLS_FILE) as f:
        raw = json.load(f)

    # adjacency: (canonical_a, canonical_b) -> {pool_id, fee, liquidity, ...}
    # We keep the best pool per pair (highest liquidity at same fee, or lowest fee)
    pools = {}
    for pool in raw:
        sym_a = pool["tokenA"]["symbol"]
        sym_b = pool["tokenB"]["symbol"]
        id_a = pool["tokenA"]["id"]
        id_b = pool["tokenB"]["id"]

        # Resolve to canonical names
        canon_a = _POOL_SYMBOL_TO_CANONICAL.get(sym_a) or _ID_TO_CANONICAL.get(id_a)
        canon_b = _POOL_SYMBOL_TO_CANONICAL.get(sym_b) or _ID_TO_CANONICAL.get(id_b)

        if not canon_a or not canon_b:
            continue  # Skip tokens we don't have in registry

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
            }

    return list(pools.values())


def build_adjacency(pools):
    """Build adjacency dict: token -> [(neighbor, pool_info)]."""
    adj = {}
    for p in pools:
        a, b = p["token_a"], p["token_b"]
        adj.setdefault(a, []).append((b, p))
        adj.setdefault(b, []).append((a, p))
    return adj


def find_best_route(adj, src, dst, max_hops=3):
    """
    BFS/DFS to find the cheapest route from src to dst.
    Score = sum of (fee / 10000) for each hop + liquidity penalty.
    Returns the best route or None.
    """
    if src == dst:
        return None

    best = None
    best_score = float("inf")

    # BFS with path tracking
    queue = [(src, [src], 0.0, [])]  # (current, path, cost, hops_info)

    while queue:
        current, path, cost, hops = queue.pop(0)

        if current == dst:
            if cost < best_score:
                best_score = cost
                best = {
                    "path": path,
                    "hops": hops,
                    "total_fee_percent": round(cost * 100, 4),
                    "num_hops": len(hops),
                }
            continue

        if len(path) - 1 >= max_hops:
            continue

        for neighbor, pool_info in adj.get(current, []):
            if neighbor in path:
                continue  # no cycles

            hop_fee = pool_info["fee"] / 1_000_000  # fee is in hundredths of bps
            # Liquidity penalty for thin pools
            liq_penalty = 0.0
            if pool_info["liquidity"] < 1_000_000:
                liq_penalty = 0.01
            elif pool_info["liquidity"] < 10_000_000:
                liq_penalty = 0.005

            hop_info = {
                "from": current,
                "to": neighbor,
                "pool_id": pool_info["pool_id"],
                "fee": pool_info["fee"],
                "fee_percent": round(pool_info["fee"] / 10000, 4),
                "token_in_id": TOKEN_REGISTRY[current]["id"],
                "token_out_id": TOKEN_REGISTRY[neighbor]["id"],
                "decimals_in": TOKEN_REGISTRY[current]["decimals"],
                "decimals_out": TOKEN_REGISTRY[neighbor]["decimals"],
                "liquidity": pool_info["liquidity"],
            }

            queue.append((
                neighbor,
                path + [neighbor],
                cost + hop_fee + liq_penalty,
                hops + [hop_info],
            ))

    return best


def build_route_table():
    """Build the complete route lookup table."""
    pools = load_pools()
    adj = build_adjacency(pools)

    tokens = sorted(adj.keys())
    print(f"Building routes for {len(tokens)} tokens across {len(pools)} pools...")

    routes = {}
    no_route = []

    for src in tokens:
        for dst in tokens:
            if src == dst:
                continue

            route = find_best_route(adj, src, dst)
            key = f"{src}->{dst}"

            if route:
                routes[key] = route
            else:
                no_route.append(key)

    # Build output
    output = {
        "version": 1,
        "token_count": len(tokens),
        "route_count": len(routes),
        "tokens": {k: TOKEN_REGISTRY[k] for k in tokens},
        "routes": routes,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(routes)} routes to {OUTPUT_FILE}")
    if no_route:
        print(f"No route found for {len(no_route)} pairs (disconnected tokens)")

    return output


if __name__ == "__main__":
    build_route_table()
