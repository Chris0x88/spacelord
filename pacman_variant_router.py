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

# Token variants - the key insight for Hedera routing
TOKEN_VARIANTS = {
    # WBTC Variants
    "WBTC_LZ": {
        "id": "0.0.1055483",
        "symbol": "WBTC[hts]",
        "type": "ERC20_BRIDGED",
        "layer": "LayerZero",
        "visible_in_hashpack": False,
        "pool_preference": "high",
        "unwrap_to": "WBTC_HTS",
        "unwrap_contract": "0.0.9675688",
        "unwrap_gas_hbar": 0.02,
    },
    "WBTC_HTS": {
        "id": "0.0.10082597",
        "symbol": "WBTC[hts]",  # Same display symbol
        "type": "HTS_NATIVE",
        "layer": "Hedera",
        "visible_in_hashpack": True,
        "pool_preference": "low",
        "wrap_to": "WBTC_LZ",
        "wrap_contract": "0.0.9675688",
        "wrap_gas_hbar": 0.02,
    },
    
    # WETH Variants
    "WETH_LZ": {
        "id": "0.0.9770617",
        "symbol": "WETH[hts]",
        "type": "ERC20_BRIDGED",
        "layer": "LayerZero",
        "visible_in_hashpack": False,
        "pool_preference": "high",
        "unwrap_to": "WETH_HTS",
        "unwrap_contract": "0.0.9675688",
        "unwrap_gas_hbar": 0.02,
    },
    "WETH_HTS": {
        "id": "0.0.541564",
        "symbol": "WETH[hts]",
        "type": "HTS_NATIVE",
        "layer": "Hedera",
        "visible_in_hashpack": True,
        "pool_preference": "low",
        "wrap_to": "WETH_LZ",
        "wrap_contract": "0.0.9675688",
        "wrap_gas_hbar": 0.02,
    },
    
    # USDC (mostly HTS, but has bridged variant)
    "USDC": {
        "id": "0.0.456858",
        "symbol": "USDC",
        "type": "ERC20_BRIDGED",
        "layer": "Circle",
        "visible_in_hashpack": True,
        "pool_preference": "high",
        "is_bridgeable_to_hts": True,
        "hts_variant": "USDC_HTS",
    },
    "USDC_HTS": {
        "id": "0.0.1055459",
        "symbol": "USDC[hts]",
        "type": "HTS_NATIVE",
        "layer": "Hedera",
        "visible_in_hashpack": True,
        "pool_preference": "high",
    },
    "HBAR": {
        "id": "0.0.0",
        "symbol": "HBAR",
        "type": "HTS_NATIVE",
        "layer": "Hedera",
        "visible_in_hashpack": True,
        "pool_preference": "high",
        "liquidity_id": "0.0.1456986", # Shared liquidity contract
    },
    "SAUCE": {
        "id": "0.0.731861",
        "symbol": "SAUCE",
        "type": "HTS_NATIVE",
        "layer": "Hedera",
        "visible_in_hashpack": True,
        "pool_preference": "high",
    },
    "XSAUCE": {
        "id": "0.0.1460200",
        "symbol": "XSAUCE",
        "type": "HTS_NATIVE",
        "layer": "Hedera",
        "visible_in_hashpack": True,
        "pool_preference": "high",
    },
    "HBARX": {
        "id": "0.0.834116",
        "symbol": "HBARX",
        "type": "HTS_NATIVE",
        "layer": "Hedera",
        "visible_in_hashpack": True,
        "pool_preference": "high",
    },
}

# Reverse lookup by ID
VARIANT_BY_ID = {v["id"]: k for k, v in TOKEN_VARIANTS.items()}

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
    
    Key insight: The "cheapest" route might give you ERC20 tokens that
    are invisible in HashPack. This router lets you choose:
    - CHEAPEST: Minimize total cost (may require manual unwrap)
    - VISIBLE: Ensure output is HTS native (HashPack friendly)
    - AUTO: Accept ERC20 if cheaper by > X%, auto-unwrap
    """
    
    BLACKLISTED_TOKENS = ["0.0.1456986"] # WHBAR is strictly blacklisted
    
    def __init__(self):
        self.pools_data = None
        self.pool_graph = {}  # (token_in, token_out) -> (pool_id, fee_bps)
        # Phase 32: Live Pricing
        from pacman_price_manager import price_manager
        self.price_manager = price_manager
        
    @property
    def htbar_price(self) -> float:
        """Get the current live HBAR price from the price manager."""
        return self.price_manager.get_hbar_price()
        
    def load_pools(self, pools_file: str = "pacman_data_raw.json"):
        """
        Load SaucerSwap pool data from a local JSON file.
        
        Args:
            pools_file: Path to the JSON file containing raw pool data.
            
        Raises:
            FileNotFoundError: If the pools_file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        try:
            with open(pools_file) as f:
                self.pools_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"❌ Critical error: {pools_file} not found. Run refresh_data.py first.")
            raise
        except json.JSONDecodeError:
            logger.error(f"❌ Critical error: {pools_file} is not a valid JSON file.")
            raise
        
        for pool in self.pools_data:
            try:
                token_a_id = pool["tokenA"]["id"]
                token_b_id = pool["tokenB"]["id"]
                
                # Map WHBAR liquidity ID (0.0.1456986) to HBAR (0.0.0) for internal routing
                if token_a_id == "0.0.1456986": token_a_id = "0.0.0"
                if token_b_id == "0.0.1456986": token_b_id = "0.0.0"

                if (token_a_id in self.BLACKLISTED_TOKENS and token_a_id != "0.0.0") or \
                   (token_b_id in self.BLACKLISTED_TOKENS and token_b_id != "0.0.0"):
                    continue

                token_a = pool["tokenA"]["symbol"]
                token_b = pool["tokenB"]["symbol"]
                token_a_id = pool["tokenA"]["id"]
                token_b_id = pool["tokenB"]["id"]
                pool_id = pool["id"]
                fee = pool["fee"]
                
                self.pool_graph[(token_a.upper(), token_b.upper())] = (pool_id, fee, token_a_id, token_b_id)
                self.pool_graph[(token_b.upper(), token_a.upper())] = (pool_id, fee, token_b_id, token_a_id)
            except KeyError as e:
                logger.warning(f"⚠️ Skipping malformed pool entry: Missing key {e}")
                continue
        
        logger.info(f"Loaded {len(self.pool_graph)//2} unique pools from {pools_file}")
    
    def find_swap_step(self, from_symbol: str, to_symbol: str) -> Optional[RouteStep]:
        """Find a direct swap between two token symbols (Case-insensitive)."""
        idx = (from_symbol.upper(), to_symbol.upper())
        if idx in self.pool_graph:
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
            # Try via multiple hubs
            potential_hubs = ["USDC", "USDC[hts]", "HBAR", "SAUCE"]
            best_hub_route = None
            
            for hub in potential_hubs:
                hub_route = self.find_hub_route(from_symbol, to_symbol, hub)
                if hub_route:
                    if best_hub_route is None or sum(s.fee_percent for s in hub_route) < sum(s.fee_percent for s in best_hub_route):
                        best_hub_route = hub_route
                        
            if best_hub_route:
                steps.extend(best_hub_route)
                total_fee = sum(s.fee_percent for s in best_hub_route)
                total_gas = sum(s.gas_estimate_hbar for s in best_hub_route)
            else:
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
