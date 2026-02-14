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
from pacman_logger import logger

# --- CONFIGURATION & PATHS ---
BASE_DIR = Path(__file__).resolve().parent
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
    
    def __init__(self, price_manager=None):
        self.pool_graph = {}  # (token_in, token_out) -> (pool_id, fee_bps, in_id, out_id)
        
        # Load Static Metadata
        self.variants = self._load_json(VARIANTS_FILE, {})
        self.pool_registry = self._load_json(POOLS_REGISTRY_FILE, [])
        
        # Build Reverse ID Map (used throughout the routing logic)
        self.variant_by_id = {v["id"]: k for k, v in self.variants.items()}

        # Phase 32: Live Pricing
        from pacman_price_manager import price_manager as pm
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
                self.pool_graph[(ta_sym, tb_sym)] = (cid, fee, ta_id, tb_id)
                self.pool_graph[(tb_sym, ta_sym)] = (cid, fee, tb_id, ta_id)

        # 2. Layer in Live Pool Data (for discovery and validation)
        try:
            with open(pools_file) as f:
                raw_data = json.load(f)
                for pool in raw_data:
                    cid = pool.get("contractId")
                    ta_id = pool.get("tokenA", {}).get("id")
                    tb_id = pool.get("tokenB", {}).get("id")
                    
                    # Skip if already in graph from registry
                    # This protects our "hand-verified" registry from being overwritten
                    check_key = (self._id_to_sym(ta_id), self._id_to_sym(tb_id))
                    if check_key in self.pool_graph:
                        continue
                        
                    # Otherwise, auto-discover if they are known tokens
                    ta_sym = self._id_to_sym(ta_id)
                    tb_sym = self._id_to_sym(tb_id)
                    
                    if ta_sym and tb_sym:
                        fee = pool.get("fee", 3000)
                        self.pool_graph[(ta_sym, tb_sym)] = (cid, fee, ta_id, tb_id)
                        self.pool_graph[(tb_sym, ta_sym)] = (cid, fee, tb_id, ta_id)
        except Exception as e:
            logger.warning(f"Live data {pools_file} not found or malformed. Using static registry only.")

        logger.info(f"Loaded {len(self.pool_graph)//2} unique pools into routing graph.")

    def _id_to_sym(self, token_id: str) -> Optional[str]:
        """Resolve a token ID to its internal routing symbol."""
        # Check variants first (our internal canonical names)
        if token_id in self.variant_by_id:
            variant_key = self.variant_by_id[token_id]
            # Strip _LZ or _HTS for the routing graph (they route the same)
            return variant_key.split("_")[0]
            
        # Fallback to HBAR
        if token_id == "0.0.0" or token_id == "0.0.1456986":
            return "HBAR"
            
        return None
    
    def find_swap_step(self, from_symbol: str, to_symbol: str) -> Optional[RouteStep]:
        """Find a direct swap between two token symbols (Case-insensitive)."""
        idx = (from_symbol.upper(), to_symbol.upper())
        if idx in self.pool_graph:
            logger.debug(f"      [✓] Direct pool found for {idx}")
            pool_id, fee_bps, id_in, id_out = self.pool_graph[idx]
            # Fix Phase 32: Fee is 3000 (0.3%). We want 0.003.
            # 3000 / 1,000,000 = 0.003
            fee_pct = fee_bps / 1_000_000 
            
            return RouteStep(
                step_type="swap",
                from_token=from_symbol,
                to_token=to_symbol,
                contract="0.0.3949434",  # SaucerSwap Router
                fee_percent=fee_pct,
                gas_estimate_hbar=0.02,  # ~0.02 HBAR
                details={"pool_id": pool_id, "fee_bps": fee_bps, "token_in_id": id_in, "token_out_id": id_out}
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
        """Get best metadata for a variant, with fallback to symbols."""
        if variant in TOKEN_VARIANTS:
            return TOKEN_VARIANTS[variant]
        
        # Fallback: Check if it matches a symbol in pools (Case-insensitive)
        variant_upper = variant.upper()
        for pool in self.pools_data:
            if pool["tokenA"]["symbol"].upper() == variant_upper:
                return {"id": pool["tokenA"]["id"], "symbol": pool["tokenA"]["symbol"], "type": "HTS_NATIVE", "visible_in_hashpack": True}
            if pool["tokenB"]["symbol"].upper() == variant_upper:
                return {"id": pool["tokenB"]["id"], "symbol": pool["tokenB"]["symbol"], "type": "HTS_NATIVE", "visible_in_hashpack": True}
        return None

    def calculate_erc20_route(self, from_variant: str, to_variant: str, amount_usd: float = 100) -> Optional[VariantRoute]:
        """
        Calculate cheapest route using ERC20 pools.
        Result may be ERC20 tokens (invisible in HashPack).
        """
        meta_in = self._get_token_meta(from_variant)
        meta_out = self._get_token_meta(to_variant)
        
        if not meta_in or not meta_out:
            logger.debug(f"      [✗] Could not resolve metadata for {from_variant} -> {to_variant}")
            return None
            
        from_symbol = meta_in["symbol"]
        to_symbol = meta_out["symbol"]
        logger.debug(f"      - Symbols: {from_symbol} -> {to_symbol}")
        
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
            # Try via multiple hubs
            potential_hubs = ["USDC", "USDC[hts]", "HBAR", "SAUCE"]
            best_hub_route = None
            
            for hub in potential_hubs:
                hub_route = self.find_hub_route(from_symbol, to_symbol, hub)
                if hub_route:
                    if best_hub_route is None or sum(s.fee_percent for s in hub_route) < sum(s.fee_percent for s in best_hub_route):
                        best_hub_route = hub_route
                        
            if best_hub_route:
                logger.debug(f"      [✓] Found route via hub")
                steps.extend(best_hub_route)
                total_fee = sum(s.fee_percent for s in best_hub_route)
                total_gas = sum(s.gas_estimate_hbar for s in best_hub_route)
            else:
                logger.debug(f"      [✗] No viable path found in graph")
                return None
        
        # Calculate total cost in HBAR
        fee_in_hbar = (amount_usd * total_fee / 100) / self.htbar_price
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
    
    def calculate_hts_route(self, from_variant: str, to_variant: str, amount_usd: float = 100) -> Optional[VariantRoute]:
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
            return self.calculate_erc20_route(from_variant, to_variant, amount_usd)
        
        # Target is ERC20, need to find HTS variant
        hts_variant = meta_out.get("unwrap_to")
        if not hts_variant:
            # If no unwrap_to, we just do ERC20 and hope for the best
            return self.calculate_erc20_route(from_variant, to_variant, amount_usd)
        
        # Option 1: Direct to HTS variant
        hts_route = self.calculate_erc20_route(from_variant, hts_variant, amount_usd)
        
        # Option 2: To ERC20 then unwrap
        erc20_route = self.calculate_erc20_route(from_variant, to_variant, amount_usd)
        if erc20_route:
            # Add unwrap step
            unwrap_gas = meta_out.get("unwrap_gas_hbar", 0.02)
            step = RouteStep(
                step_type="unwrap",
                from_token=meta_out["symbol"],
                to_token=TOKEN_VARIANTS[hts_variant]["symbol"],
                contract=meta_out.get("unwrap_contract", "0.0.9675688"),
                gas_estimate_hbar=unwrap_gas
            )
            erc20_route.steps.append(step)
            erc20_route.to_variant = hts_variant
            erc20_route.hashpack_visible = True
            erc20_route.total_gas_hbar += unwrap_gas
            erc20_route.total_cost_hbar += unwrap_gas
            
            if not hts_route or erc20_route.total_cost_hbar < hts_route.total_cost_hbar:
                return erc20_route
        
        return hts_route
    
    def get_all_routes(self, from_variant: str, to_variant: str, amount_usd: float = 100) -> List[VariantRoute]:

        """Get all possible routes for comparison."""
        routes = []
        
        # Route via ERC20 (cheapest, may be invisible)
        erc20_route = self.calculate_erc20_route(from_variant, to_variant, amount_usd)
        if erc20_route:
            routes.append(erc20_route)
        
        # Route to HTS (HashPack visible)
        hts_route = self.calculate_hts_route(from_variant, to_variant, amount_usd)
        if hts_route and hts_route not in routes:
            routes.append(hts_route)
        
        return sorted(routes, key=lambda r: r.total_cost_hbar)
    
    def recommend_route(self, from_variant: str, to_variant: str, 
                       user_preference: str = "auto",
                       amount_usd: float = 100) -> Optional[VariantRoute]:
        """
        Recommend best route based on user preference.
        
        user_preference:
        - "cheapest": Lowest cost, even if ERC20
        - "visible": HTS only (HashPack friendly)
        - "auto": ERC20 acceptable if saves > 5%
        """
        routes = self.get_all_routes(from_variant, to_variant, amount_usd)
        
        if not routes:
            return None
        
        if user_preference == "cheapest":
            return routes[0]
        
        elif user_preference == "visible":
            for route in routes:
                if route.hashpack_visible:
                    return route
            return None
        
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
        
        route = router.recommend_route(from_variant, to_variant, preference, amount_usd=100)
        
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
