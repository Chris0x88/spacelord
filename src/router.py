#!/usr/bin/env python3
"""
Pacman Variant Router - Handles ERC20 vs HTS token variants
The ultimate routing engine that understands dual-token formats on Hedera.
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Use centralized logger
from src.logger import logger

# --- CONFIGURATION & PATHS ---
BASE_DIR = Path(__file__).resolve().parent.parent # Root dir
DATA_DIR = BASE_DIR / "data"
VARIANTS_FILE = DATA_DIR / "variants.json"
POOLS_REGISTRY_FILE = DATA_DIR / "pools.json"

@dataclass
class RouteStep:
    """A single step in a multi-step route."""
    step_type: str  # "swap", "wrap", "unwrap", "bridge"
    from_token: str
    to_token: str
    contract: str
    gas_estimate_hbar: float
    fee_percent: float = 0.0
    details: dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class VariantRoute:
    """A complete route including swaps and wrap/unwraps."""
    from_variant: str
    to_variant: str
    steps: List[RouteStep]
    total_fee_percent: float
    total_gas_hbar: float
    total_cost_hbar: float  # Fees + gas in HBAR equivalent
    estimated_time_seconds: int
    output_format: str  # "ERC20" or "HTS"
    hashpack_visible: bool
    confidence: float
    
    def explain(self) -> str:
        """Human-readable explanation of the route."""
        lines = [
            f"Route: {self.from_variant} → {self.to_variant}",
            f"Output Format: {'HTS (HashPack visible)' if self.hashpack_visible else 'ERC20 (HashPack invisible)'}",
            f"Total Cost: {self.total_fee_percent * 100:.2f}% + {self.total_gas_hbar:.3f} HBAR",
            f"Steps ({len(self.steps)}):",
        ]
        for i, step in enumerate(self.steps, 1):
            if step.step_type == "swap":
                lines.append(f"  {i}. Swap {step.from_token} → {step.to_token} ({step.fee_percent * 100:.2f}%)")
            elif step.step_type == "unwrap":
                lines.append(f"  {i}. Unwrap {step.from_token} → {step.to_token} (gas: {step.gas_estimate_hbar:.3f} HBAR)")
            elif step.step_type == "wrap":
                lines.append(f"  {i}. Wrap {step.from_token} → {step.to_token} (gas: {step.gas_estimate_hbar:.3f} HBAR)")
        return "\n".join(lines)

class PacmanVariantRouter:
    """
    Ultimate router that understands Hedera's dual-token system.
    
    WHY: Decouples structural metadata (variants/pools) from live liquidity data,
    providing a stable registry that survives API fluctuations.
    """
    
    # WHBAR is strictly blacklisted for UI, but used for internal routing
    BLACKLISTED_TOKENS = ["0.0.1456986"]
    
    # Canonical token defaults — human-friendly names → internal variant keys
    # These MUST always resolve. Users say "bitcoin", agents say "WBTC_HTS".
    CANONICAL_DEFAULTS = {
        "bitcoin": "WBTC_HTS", "btc": "WBTC_HTS", "wbtc": "WBTC_HTS",
        "ethereum": "WETH_HTS", "eth": "WETH_HTS", "weth": "WETH_HTS",
        "dollar": "USDC", "usd": "USDC", "usdc": "USDC", "stablecoin": "USDC",
        "hbar": "HBAR", "hedera": "HBAR",
    }
    
    def __init__(self, price_manager=None):
        self.pool_graph = {}  # (token_in, token_out) -> (pool_id, fee_bps, in_id, out_id, liquidity_usd)
        self.pools_data = []  # Store raw pool data for metadata lookup
        
        # Load Static Metadata
        self.variants = self._load_json(VARIANTS_FILE, {})
        self.pool_registry = self._load_json(POOLS_REGISTRY_FILE, [])
        
        # Build Reverse ID Map (for variants.json — 8 canonical tokens)
        self.variant_by_id = {v["id"]: k for k, v in self.variants.items()}
        
        # Build extended token map from tokens.json (for ALL approved tokens)
        # This is the fix for why approved tokens couldn't be found in _id_to_sym
        self._tokens_data = self._load_json(DATA_DIR / "tokens.json", {})
        self.token_by_id = {}  # id -> {id, symbol, decimals, ...}
        for sym_key, meta in self._tokens_data.items():
            if isinstance(meta, dict) and "id" in meta:
                self.token_by_id[meta["id"]] = meta

        # Phase 32: Live Pricing
        from lib.prices import price_manager as pm
        self.price_manager = price_manager or pm
        
    def _load_json(self, path: Path, default):
        try:
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load static file {path.name}: {e}")
        return default

    @property
    def htbar_price(self) -> float:
        """Get the current live HBAR price from the price manager."""
        return self.price_manager.get_hbar_price()
        
    def load_pools(self, pools_file: str = "data/pacman_data_raw.json"):
        """
        Populate the routing graph.
        
        WHY: We build the "map" using our static pool registry (the source of truth
        for structural integrity) and then layer in live data for routing weighting.
        """
        # 1. Initialize Graph from Static Registry
        # This ensures we CAN route even if the API refresh fails temporarily.
        for entry in self.pool_registry:
            cid = entry.get("contractId")
            ta_id = entry.get("tokenA")
            tb_id = entry.get("tokenB")
            fee = entry.get("fee", 3000)
            
            # Resolve symbols for the graph keys
            ta_sym = self._id_to_sym(ta_id)
            tb_sym = self._id_to_sym(tb_id)
            
            if ta_sym and tb_sym:
                if not self._is_blacklisted(ta_sym, tb_sym):
                    # Static registry has no liquidity data; use 0 as sentinel
                    self.pool_graph[(ta_sym, tb_sym)] = (cid, fee, ta_id, tb_id, 0.0)
                    self.pool_graph[(tb_sym, ta_sym)] = (cid, fee, tb_id, ta_id, 0.0)
                else:
                    logger.warning(f"Skipping blacklisted pool {ta_sym}<->{tb_sym}")

        # 2. Layer in Live Pool Data (for discovery, validation, AND liquidity)
        try:
            with open(pools_file) as f:
                raw_data = json.load(f)
                self.pools_data = raw_data  # Keep reference for metadata lookup
                for pool in raw_data:
                    cid = pool.get("contractId")
                    ta = pool.get("tokenA", {})
                    tb = pool.get("tokenB", {})
                    ta_id = ta.get("id")
                    tb_id = tb.get("id")
                    
                    ta_sym = self._id_to_sym(ta_id)
                    tb_sym = self._id_to_sym(tb_id)
                    
                    if not (ta_sym and tb_sym):
                        continue
                    if self._is_blacklisted(ta_sym, tb_sym):
                        continue
                    
                    fee = pool.get("fee", 3000)
                    
                    # Calculate pool liquidity in USD from pool-level amounts
                    # Pool data has amountA/amountB at top level, prices inside token dicts
                    liq_usd = self._estimate_pool_liquidity_usd(
                        ta, tb,
                        pool_amount_a=pool.get("amountA", 0),
                        pool_amount_b=pool.get("amountB", 0)
                    )
                    
                    # Update existing entries WITH liquidity data, or add new ones
                    existing = self.pool_graph.get((ta_sym, tb_sym))
                    if existing and existing[4] > 0:
                        # Keep the deeper pool if we already have one
                        if liq_usd > existing[4]:
                            self.pool_graph[(ta_sym, tb_sym)] = (cid, fee, ta_id, tb_id, liq_usd)
                            self.pool_graph[(tb_sym, ta_sym)] = (cid, fee, tb_id, ta_id, liq_usd)
                    else:
                        self.pool_graph[(ta_sym, tb_sym)] = (cid, fee, ta_id, tb_id, liq_usd)
                        self.pool_graph[(tb_sym, ta_sym)] = (cid, fee, tb_id, ta_id, liq_usd)
        except Exception as e:
            logger.warning(f"Live data {pools_file} not found or malformed. Using static registry only.")

        logger.info(f"Loaded {len(self.pool_graph)//2} unique pools into routing graph.")

    def _is_blacklisted(self, sym_a: str, sym_b: str) -> bool:
        """Check if a pair is blacklisted for direct routing."""
        # broken pools or low liquidity direct pairs that should be routed via hub
        BLACKLIST = [
            {"HBAR", "WBTC[HTS]"}, # Old format, left for safety
            {"HBAR", "HTS-WBTC"},  # Direct pool is broken/reverting. Match _id_to_sym output.
        ]
        pair = {sym_a.upper(), sym_b.upper()}
        return pair in BLACKLIST

    def _id_to_sym(self, token_id: str) -> Optional[str]:
        """Resolve a token ID to its internal routing symbol."""
        # Native HBAR and its wrapped form both map to "HBAR"
        if token_id == "0.0.0" or token_id == "0.0.1456986":
            return "HBAR"

        # 1. Check variants.json (canonical names for known variant tokens)
        if token_id in self.variant_by_id:
            variant_key = self.variant_by_id[token_id]
            return self.variants[variant_key]["symbol"].upper()
        
        # 2. Fallback: check tokens.json (all approved tokens via `pools approve`)
        if token_id in self.token_by_id:
            return self.token_by_id[token_id]["symbol"].upper()
            
        return None
    
    def _estimate_pool_liquidity_usd(self, token_a: dict, token_b: dict,
                                       pool_amount_a: int = 0, pool_amount_b: int = 0) -> float:
        """Estimate total pool liquidity in USD from pool amounts and token prices."""
        try:
            price_a = float(token_a.get("priceUsd", 0))
            price_b = float(token_b.get("priceUsd", 0))
            decimals_a = int(token_a.get("decimals", 8))
            decimals_b = int(token_b.get("decimals", 8))
            
            # Use pool-level amounts (amountA/amountB from pool dict)
            amount_a = int(pool_amount_a) if pool_amount_a else 0
            amount_b = int(pool_amount_b) if pool_amount_b else 0
            
            usd_a = (amount_a / (10 ** decimals_a)) * price_a if price_a > 0 and amount_a > 0 else 0
            usd_b = (amount_b / (10 ** decimals_b)) * price_b if price_b > 0 and amount_b > 0 else 0
            return usd_a + usd_b
        except (ValueError, TypeError):
            return 0.0

    def find_swap_step(self, from_symbol: str, to_symbol: str) -> Optional[RouteStep]:
        """Find a direct swap between two token symbols (Case-insensitive)."""
        idx = (from_symbol.upper(), to_symbol.upper())
        if idx in self.pool_graph:
            pool_id, fee_bps, id_in, id_out, liquidity_usd = self.pool_graph[idx]
            # Fee is 3000 (0.3%). We want 0.003 for human readable reporting.
            fee_pct = fee_bps / 1_000_000 
            
            return RouteStep(
                step_type="swap",
                from_token=from_symbol,
                to_token=to_symbol,
                contract="0.0.3949434",  # SaucerSwap Router
                fee_percent=fee_pct,
                gas_estimate_hbar=0.02,
                details={
                    "pool_id": pool_id, "fee_bps": fee_bps,
                    "token_in_id": id_in, "token_out_id": id_out,
                    "liquidity_usd": liquidity_usd
                }
            )
        return None
    
    def find_hub_route(self, from_symbol: str, to_symbol: str, hub: str = "USDC") -> Optional[List[RouteStep]]:
        """Find a route via a hub token (USDC, WHBAR, etc.)."""
        step1 = self.find_swap_step(from_symbol, hub)
        step2 = self.find_swap_step(hub, to_symbol)
        
        if step1 and step2:
            return [step1, step2]
        return None
    
    def _get_token_meta(self, variant: str) -> Optional[dict]:
        """Get best metadata for a variant, with fallback to tokens.json and pool data."""
        # 1. Check variants.json first (canonical)
        if variant in self.variants:
            return self.variants[variant]
        
        # 2. Check tokens.json (all approved tokens — key is uppercase symbol)
        variant_upper = variant.upper()
        for sym_key, meta in self._tokens_data.items():
            if sym_key.upper() == variant_upper or (isinstance(meta, dict) and meta.get("symbol", "").upper() == variant_upper):
                if isinstance(meta, dict):
                    return {
                        "id": meta.get("id"),
                        "symbol": meta.get("symbol", sym_key),
                        "type": "HTS_NATIVE",
                        "visible_in_hashpack": True,
                        "decimals": meta.get("decimals", 8)
                    }
        
        # 3. Fallback: pool live data symbols
        for pool in self.pools_data:
            if pool.get("tokenA", {}).get("symbol", "").upper() == variant_upper:
                ta = pool["tokenA"]
                return {"id": ta["id"], "symbol": ta["symbol"], "type": "HTS_NATIVE", "visible_in_hashpack": True}
            if pool.get("tokenB", {}).get("symbol", "").upper() == variant_upper:
                tb = pool["tokenB"]
                return {"id": tb["id"], "symbol": tb["symbol"], "type": "HTS_NATIVE", "visible_in_hashpack": True}
        return None

    def calculate_erc20_route(self, from_variant: str, to_variant: str, volume_usd: float = 100) -> Optional[VariantRoute]:
        """
        Calculate best route using cost-aware hub strategy.
        
        Route scoring considers the FULL cost:
        - LP fees (fee_percent per hop)
        - Price impact estimate (trade_size / pool_liquidity)
        - Gas cost (HBAR per step, converted to fee-equivalent)
        """
        meta_in = self._get_token_meta(from_variant)
        meta_out = self._get_token_meta(to_variant)
        
        if not meta_in or not meta_out:
            return None
            
        from_symbol = meta_in["symbol"]
        to_symbol = meta_out["symbol"]
        
        steps = []
        total_fee = 0.0
        total_gas = 0.0
        
        # Try direct swap first
        direct = self.find_swap_step(from_symbol, to_symbol)
        if direct:
            steps.append(direct)
            total_fee = direct.fee_percent
            total_gas = direct.gas_estimate_hbar
        else:
            # Try via multiple hubs — score by FULL effective cost
            potential_hubs = ["USDC", "USDC[hts]", "HBAR", "SAUCE"]
            best_hub_route = None
            best_score = float('inf')
            
            for hub in potential_hubs:
                hub_route = self.find_hub_route(from_symbol, to_symbol, hub)
                if hub_route:
                    score = self._score_route(hub_route, volume_usd)
                    if score < best_score:
                        best_score = score
                        best_hub_route = hub_route
                        
            if best_hub_route:
                steps.extend(best_hub_route)
                total_fee = sum(s.fee_percent for s in best_hub_route)
                total_gas = sum(s.gas_estimate_hbar for s in best_hub_route)
            else:
                return None
        
        # Calculate total cost in HBAR
        fee_in_hbar = (volume_usd * total_fee) / self.htbar_price if self.htbar_price > 0 else 0
        total_cost = fee_in_hbar + total_gas
        
        return VariantRoute(
            from_variant=from_variant,
            to_variant=to_variant,
            steps=steps,
            total_fee_percent=total_fee,
            total_gas_hbar=total_gas,
            total_cost_hbar=total_cost,
            estimated_time_seconds=5 * len(steps),
            output_format="ERC20" if meta_out.get("type") == "ERC20_BRIDGED" else "HTS",
            hashpack_visible=meta_out.get("visible_in_hashpack", True),
            confidence=0.95 if len(steps) == 1 else 0.85
        )
    
    def resolve_canonical(self, name: str) -> str:
        """Resolve human-friendly names to internal variant keys.
        
        'bitcoin' → 'WBTC_HTS', 'dollar' → 'USDC', etc.
        Returns the original name if no canonical mapping exists.
        """
        return self.CANONICAL_DEFAULTS.get(name.lower().strip(), name)

    def _score_route(self, steps: List[RouteStep], volume_usd: float) -> float:
        """
        Score a route by total effective cost.
        
        Components:
        1. LP fees (sum of fee_percent across hops)
        2. Price impact estimate (volume / pool_liquidity per hop)
        3. Gas cost as fee-equivalent (gas_hbar * hbar_price / volume_usd)
        
        Lower score = better route.
        """
        # Guard: ensure volume is positive to avoid division by zero
        safe_volume = max(volume_usd, 1.0)
        
        total_fee_pct = sum(s.fee_percent for s in steps)
        
        # Estimate price impact from liquidity depth
        total_impact = 0.0
        for step in steps:
            liq = step.details.get("liquidity_usd", 0)
            if liq > 0:
                total_impact += safe_volume / (2.0 * liq)
            else:
                total_impact += 0.01  # 1% penalty for unknown depth
        
        # Gas cost as a percentage of trade value
        total_gas_hbar = sum(s.gas_estimate_hbar for s in steps)
        gas_cost_pct = 0.0
        if self.htbar_price > 0:
            gas_cost_usd = total_gas_hbar * self.htbar_price
            gas_cost_pct = gas_cost_usd / safe_volume
        
        return total_fee_pct + total_impact + gas_cost_pct
    
    def calculate_hts_route(self, from_variant: str, to_variant: str, volume_usd: float = 100) -> Optional[VariantRoute]:
        """
        Calculate route to HTS-native output (visible in HashPack).
        If ERC20 is cheaper, adds unwrap step.
        """
        meta_in = self._get_token_meta(from_variant)
        meta_out = self._get_token_meta(to_variant)
        
        if not meta_in or not meta_out:
            return None
            
        # If target already HTS, standard routing is fine
        if meta_out.get("type") == "HTS_NATIVE":
            return self.calculate_erc20_route(from_variant, to_variant, volume_usd)
        
        # Target is ERC20, need to find HTS variant
        hts_variant = meta_out.get("unwrap_to")
        if not hts_variant:
            # If no unwrap_to, we just do ERC20 and hope for the best
            return self.calculate_erc20_route(from_variant, to_variant, volume_usd)
        
        # Option 1: Direct to HTS variant
        hts_route = self.calculate_erc20_route(from_variant, hts_variant, volume_usd)
        
        # Option 2: To ERC20 then unwrap
        erc20_route = self.calculate_erc20_route(from_variant, to_variant, volume_usd)
        if erc20_route:
            # Add unwrap step
            unwrap_gas = meta_out.get("unwrap_gas_hbar", 0.02)
            step = RouteStep(
                step_type="unwrap",
                from_token=meta_out["symbol"],
                to_token=self.variants[hts_variant]["symbol"],
                contract=meta_out.get("unwrap_contract", "0.0.9675688"),
                gas_estimate_hbar=unwrap_gas,
                details={"token_in_id": meta_out["id"], "token_out_id": self.variants[hts_variant]["id"]}
            )
            erc20_route.steps.append(step)
            erc20_route.to_variant = hts_variant
            erc20_route.hashpack_visible = True
            erc20_route.total_gas_hbar += unwrap_gas
            erc20_route.total_cost_hbar += unwrap_gas
            
            if not hts_route or erc20_route.total_cost_hbar < hts_route.total_cost_hbar:
                return erc20_route
        
        return hts_route
    
    def get_all_routes(self, from_variant: str, to_variant: str, volume_usd: float = 100) -> List[VariantRoute]:

        """Get all possible routes for comparison."""
        routes = []
        
        # Route via ERC20 (cheapest, may be invisible)
        erc20_route = self.calculate_erc20_route(from_variant, to_variant, volume_usd)
        if erc20_route:
            routes.append(erc20_route)
        
        # Route to HTS (HashPack visible)
        hts_route = self.calculate_hts_route(from_variant, to_variant, volume_usd)
        if hts_route and hts_route not in routes:
            routes.append(hts_route)
        
        return sorted(routes, key=lambda r: r.total_cost_hbar)
    
    def calculate_strict_wrap_route(self, from_variant: str, to_variant: str, volume_usd: float = 100) -> Optional[VariantRoute]:
        """
        Calculate a strict Wrap/Unwrap route.
        Returns a route ONLY if `from` -> `to` is a direct wrap/unwrap pair defined in variants.json.
        """
        meta_in = self._get_token_meta(from_variant)
        meta_out = self._get_token_meta(to_variant)
        
        if not meta_in or not meta_out:
            return None

        # SAFETY: Prevent HBAR <-> WHBAR routing. User has flagged this as unsafe/lossy.
        # WHBAR (0.0.1456986) is internal routing only.
        if (meta_in.get("symbol") == "HBAR" and meta_out.get("id") == "0.0.1456986") or \
           (meta_in.get("id") == "0.0.1456986" and meta_out.get("symbol") == "HBAR"):
            logger.warning("SAFETY: Explicitly blocked HBAR <-> WHBAR wrap/unwrap.")
            return None

        # Check Wrap (HTS -> LZ)
        if meta_in.get("wrap_to") == to_variant:
            wrap_gas = meta_in.get("wrap_gas_hbar", 0.02)
            return VariantRoute(
                from_variant=from_variant,
                to_variant=to_variant,
                steps=[RouteStep(
                    step_type="wrap",
                    from_token=meta_in["symbol"],
                    to_token=meta_out["symbol"],
                    contract=meta_in.get("wrap_contract", "0.0.9675688"),
                    gas_estimate_hbar=wrap_gas,
                    details={"token_in_id": meta_in["id"], "token_out_id": meta_out["id"]}
                )],
                total_fee_percent=0.0,
                total_gas_hbar=wrap_gas,
                total_cost_hbar=wrap_gas,
                estimated_time_seconds=5,
                output_format="ERC20", 
                hashpack_visible=meta_out.get("visible_in_hashpack", False),
                confidence=1.0
            )

        # Check Unwrap (LZ -> HTS)
        if meta_in.get("unwrap_to") == to_variant:
            unwrap_gas = meta_in.get("unwrap_gas_hbar", 0.02)
            return VariantRoute(
                from_variant=from_variant,
                to_variant=to_variant,
                steps=[RouteStep(
                    step_type="unwrap",
                    from_token=meta_in["symbol"],
                    to_token=meta_out["symbol"],
                    contract=meta_in.get("unwrap_contract", "0.0.9675688"),
                    gas_estimate_hbar=unwrap_gas,
                    details={"token_in_id": meta_in["id"], "token_out_id": meta_out["id"]}
                )],
                total_fee_percent=0.0,
                total_gas_hbar=unwrap_gas,
                total_cost_hbar=unwrap_gas,
                estimated_time_seconds=5,
                output_format="HTS",
                hashpack_visible=meta_out.get("visible_in_hashpack", True),
                confidence=1.0
            )
            
        return None

    def recommend_route(self, from_variant: str, to_variant: str, 
                       user_preference: str = "auto",
                       volume_usd: float = 100) -> VariantRoute:
        """
        Recommend best route for a SWAP. NEVER returns None.
        
        Logic:
        0. Resolve canonical names (bitcoin → WBTC_HTS, etc.)
        1. Check if it's a direct Wrap/Unwrap (Efficiency Check).
        2. If not, perform full graph search for Swap routes.
        3. If all fail, return an error route with explanation.
        """
        # 0. Resolve canonical names
        from_variant = self.resolve_canonical(from_variant)
        to_variant = self.resolve_canonical(to_variant)
        
        # 1. Efficiency Check: Is this just a wrap?
        direct_wrap = self.calculate_strict_wrap_route(from_variant, to_variant, volume_usd)
        if direct_wrap:
            return direct_wrap

        # 2. Graph Search (Swaps)
        routes = self.get_all_routes(from_variant, to_variant, volume_usd)
        
        if not routes:
            # --- NEVER-FAIL: Return error route with explanation ---
            reasons = []
            meta_in = self._get_token_meta(from_variant)
            meta_out = self._get_token_meta(to_variant)
            if not meta_in:
                reasons.append(f"Token '{from_variant}' not found. Run 'pools search {from_variant}' to discover pools.")
            if not meta_out:
                reasons.append(f"Token '{to_variant}' not found. Run 'pools search {to_variant}' to discover pools.")
            if meta_in and meta_out:
                reasons.append(f"No liquidity path between {from_variant} and {to_variant}. Try approving more pools with 'pools search'.")
            
            logger.warning(f"Router: No route {from_variant} → {to_variant}: {'; '.join(reasons)}")
            return VariantRoute(
                from_variant=from_variant,
                to_variant=to_variant,
                steps=[],
                total_fee_percent=0.0,
                total_gas_hbar=0.0,
                total_cost_hbar=0.0,
                estimated_time_seconds=0,
                output_format="ERROR",
                hashpack_visible=False,
                confidence=0.0
            )
            
        if user_preference == "cheapest":
            return routes[0]
        
        elif user_preference == "visible":
            for route in routes:
                if route.hashpack_visible:
                    return route
            return routes[0]  # Fallback to cheapest if no visible route
        
        elif user_preference == "auto":
            cheapest = routes[0]
            if cheapest.hashpack_visible:
                return cheapest
            
            # Find HTS alternative
            for route in routes:
                if route.hashpack_visible:
                    # Accept ERC20 if saves > 5%
                    if cheapest.total_cost_hbar < route.total_cost_hbar * 0.95:
                        return cheapest
                    return route
            return cheapest
        
        return routes[0]  # Default to cheapest

# =============================================================================
# CLI Testing
# =============================================================================

def test_variant_router():
    """Test the variant router."""
    print("="*80)
    print("🧠 PACMAN VARIANT ROUTER - TEST SUITE")
    print("="*80)
    
    router = PacmanVariantRouter()
    router.load_pools()
    
    # Test cases
    test_cases = [
        ("USDC", "WBTC_LZ", "cheapest", "Route to ERC20 WBTC (invisible)"),
        ("USDC", "WBTC_HTS", "visible", "Route to HTS WBTC (visible in HashPack)"),
        ("USDC", "WBTC_HTS", "auto", "Auto-choose based on cost savings"),
    ]
    
    for from_variant, to_variant, preference, description in test_cases:
        print(f"\n{'='*80}")
        print(f"Test: {description}")
        print(f"From: {from_variant} → To: {to_variant} | Preference: {preference}")
        print("="*80)
        
        route = router.recommend_route(from_variant, to_variant, preference, volume_usd=100)
        
        if route:
            print(route.explain())
            print(f"\n💰 Total Cost: {route.total_cost_hbar:.4f} HBAR")
            print(f"👁️  HashPack Visible: {'Yes' if route.hashpack_visible else 'No (manual unwrap needed)'}")
            print(f"🎯 Confidence: {route.confidence:.0%}")
        else:
            print("❌ No route found")
    
    return 0

if __name__ == "__main__":
    exit(test_variant_router())
