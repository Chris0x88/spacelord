#!/usr/bin/env python3
"""
Pacman Ultimate Matrix - Complete routing with ERC20/HTS variants
Includes swap paths, wrap/unwrap, and cost optimization.
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Import variant definitions
from pacman_variant_router import TOKEN_VARIANTS, VARIANT_BY_ID

@dataclass
class UltimateRoute:
    """Complete route with all metadata for AI training."""
    route_id: str
    from_token: str
    to_token: str
    path: List[str]
    steps: List[Dict]
    total_fee_bps: int
    total_gas_hbar: float
    total_cost_hbar: float
    output_variant: str
    hashpack_visible: bool
    requires_wrap_unwrap: bool
    estimated_output_usd: float
    complexity: str  # "SIMPLE", "MEDIUM", "COMPLEX"

class PacmanUltimateMatrix:
    """
    The ultimate routing matrix that handles ALL Hedera token complexities:
    - ERC20 vs HTS variants
    - Wrap/unwrap operations
    - Cost optimization across formats
    - User preference integration
    """
    
    def __init__(self):
        self.pools_data = None
        self.pool_graph = {}
        self.routes = []
        self.htbar_price = 0.09139659
        
    def load_pools(self, pools_file: str = "pacman_data_raw.json"):
        """Load and index all SaucerSwap pools."""
        with open(pools_file) as f:
            self.pools_data = json.load(f)
        
        for pool in self.pools_data:
            token_a = pool["tokenA"]["symbol"]
            token_b = pool["tokenB"]["symbol"]
            pool_id = pool["id"]
            fee = pool["fee"]
            
            self.pool_graph[(token_a, token_b)] = (pool_id, fee)
            self.pool_graph[(token_b, token_a)] = (pool_id, fee)
    
    def build_matrix(self, amount_usd: float = 100):
        """Build complete routing matrix with all variants."""
        
        # Core token pairs to map
        token_pairs = [
            ("USDC", "WBTC_LZ"),
            ("USDC", "WBTC_HTS"),
            ("USDC", "WETH_LZ"),
            ("USDC", "WETH_HTS"),
            ("WBTC_LZ", "USDC"),
            ("WBTC_HTS", "USDC"),
            ("WETH_LZ", "USDC"),
            ("WETH_HTS", "USDC"),
        ]
        
        print(f"Building ultimate matrix for {len(token_pairs)} token pairs...")
        
        for from_variant, to_variant in token_pairs:
            routes = self.calculate_routes_for_pair(from_variant, to_variant, amount_usd)
            self.routes.extend(routes)
        
        print(f"\n✅ Built {len(self.routes)} complete routes")
        return self.routes
    
    def calculate_routes_for_pair(self, from_variant: str, to_variant: str, amount_usd: float) -> List[UltimateRoute]:
        """Calculate all possible routes between two token variants."""
        routes = []
        
        from_symbol = TOKEN_VARIANTS[from_variant]["symbol"]
        to_symbol = TOKEN_VARIANTS[to_variant]["symbol"]
        
        # Path 1: Direct swap (if pools exist)
        direct_route = self.try_direct_route(from_variant, to_variant, amount_usd)
        if direct_route:
            routes.append(direct_route)
        
        # Path 2: Via USDC hub
        usdc_route = self.try_hub_route(from_variant, to_variant, "USDC", amount_usd)
        if usdc_route:
            routes.append(usdc_route)
        
        # Path 3: Via USDC[hts] hub
        usdc_hts_route = self.try_hub_route(from_variant, to_variant, "USDC[hts]", amount_usd)
        if usdc_hts_route:
            routes.append(usdc_hts_route)
        
        # Path 4: Via WHBAR hub
        whbar_route = self.try_hub_route(from_variant, to_variant, "HBAR", amount_usd)
        if whbar_route:
            routes.append(whbar_route)
        
        # If output should be HTS but we only found ERC20 routes, add unwrap
        if TOKEN_VARIANTS[to_variant]["type"] == "HTS_NATIVE":
            for route in routes[:]:
                if not route.hashpack_visible and TOKEN_VARIANTS[to_variant].get("unwrap_to"):
                    unwrap_route = self.add_unwrap_step(route, to_variant)
                    if unwrap_route:
                        routes.append(unwrap_route)
        
        return routes
    
    def try_direct_route(self, from_variant: str, to_variant: str, amount_usd: float) -> Optional[UltimateRoute]:
        """Try to find a direct swap route."""
        from_symbol = TOKEN_VARIANTS[from_variant]["symbol"]
        to_symbol = TOKEN_VARIANTS[to_variant]["symbol"]
        
        if (from_symbol, to_symbol) in self.pool_graph:
            pool_id, fee_bps = self.pool_graph[(from_symbol, to_symbol)]
            fee_pct = fee_bps / 10000
            gas_hbar = 0.02
            
            fee_in_hbar = (amount_usd * fee_pct / 100) / self.htbar_price
            total_cost = fee_in_hbar + gas_hbar
            
            return UltimateRoute(
                route_id=f"{from_variant}_to_{to_variant}_direct",
                from_token=from_variant,
                to_token=to_variant,
                path=[from_variant, to_variant],
                steps=[{
                    "type": "swap",
                    "from": from_symbol,
                    "to": to_symbol,
                    "pool_id": pool_id,
                    "fee_bps": fee_bps,
                    "contract": "0.0.3949434"
                }],
                total_fee_bps=fee_bps,
                total_gas_hbar=gas_hbar,
                total_cost_hbar=total_cost,
                output_variant=to_variant,
                hashpack_visible=TOKEN_VARIANTS[to_variant]["visible_in_hashpack"],
                requires_wrap_unwrap=False,
                estimated_output_usd=amount_usd * (1 - fee_pct/100),
                complexity="SIMPLE"
            )
        return None
    
    def try_hub_route(self, from_variant: str, to_variant: str, hub: str, amount_usd: float) -> Optional[UltimateRoute]:
        """Try to find a route via a hub token."""
        from_symbol = TOKEN_VARIANTS[from_variant]["symbol"]
        to_symbol = TOKEN_VARIANTS[to_variant]["symbol"]
        
        # Check if both legs exist
        leg1 = self.pool_graph.get((from_symbol, hub))
        leg2 = self.pool_graph.get((hub, to_symbol))
        
        if leg1 and leg2:
            pool1, fee1 = leg1
            pool2, fee2 = leg2
            total_fee_bps = fee1 + fee2
            total_gas = 0.035  # 2 hops
            
            fee_pct = total_fee_bps / 10000
            fee_in_hbar = (amount_usd * fee_pct / 100) / self.htbar_price
            total_cost = fee_in_hbar + total_gas
            
            return UltimateRoute(
                route_id=f"{from_variant}_to_{to_variant}_via_{hub}",
                from_token=from_variant,
                to_token=to_variant,
                path=[from_variant, hub, to_variant],
                steps=[
                    {
                        "type": "swap",
                        "from": from_symbol,
                        "to": hub,
                        "pool_id": pool1,
                        "fee_bps": fee1,
                        "contract": "0.0.3949434"
                    },
                    {
                        "type": "swap",
                        "from": hub,
                        "to": to_symbol,
                        "pool_id": pool2,
                        "fee_bps": fee2,
                        "contract": "0.0.3949434"
                    }
                ],
                total_fee_bps=total_fee_bps,
                total_gas_hbar=total_gas,
                total_cost_hbar=total_cost,
                output_variant=to_variant,
                hashpack_visible=TOKEN_VARIANTS[to_variant]["visible_in_hashpack"],
                requires_wrap_unwrap=False,
                estimated_output_usd=amount_usd * (1 - fee_pct/100),
                complexity="MEDIUM"
            )
        return None
    
    def add_unwrap_step(self, route: UltimateRoute, target_variant: str) -> Optional[UltimateRoute]:
        """Add an unwrap step to convert ERC20 to HTS."""
        if not TOKEN_VARIANTS[target_variant].get("unwrap_to"):
            return None
        
        unwrap_gas = TOKEN_VARIANTS[target_variant].get("unwrap_gas_hbar", 0.02)
        new_gas = route.total_gas_hbar + unwrap_gas
        new_cost = route.total_cost_hbar + unwrap_gas
        
        # Create copy with unwrap step
        new_steps = route.steps.copy()
        new_steps.append({
            "type": "unwrap",
            "from": route.to_token,
            "to": target_variant,
            "contract": TOKEN_VARIANTS[target_variant]["unwrap_contract"],
            "gas_hbar": unwrap_gas
        })
        
        return UltimateRoute(
            route_id=f"{route.route_id}_with_unwrap",
            from_token=route.from_token,
            to_token=target_variant,
            path=route.path + [target_variant],
            steps=new_steps,
            total_fee_bps=route.total_fee_bps,
            total_gas_hbar=new_gas,
            total_cost_hbar=new_cost,
            output_variant=target_variant,
            hashpack_visible=True,  # Now visible!
            requires_wrap_unwrap=True,
            estimated_output_usd=route.estimated_output_usd,
            complexity="COMPLEX" if len(new_steps) > 2 else "MEDIUM"
        )
    
    def export_training_data(self, output_dir: str = "training_data"):
        """Export complete training dataset for AI."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 1. Complete routing matrix
        with open(output_path / "ultimate_matrix.json", "w") as f:
            json.dump([asdict(r) for r in self.routes], f, indent=2)
        
        # 2. Training examples with natural language
        training_examples = []
        
        for route in self.routes:
            amounts = [100, 500, 1000, 5000]
            for amount in amounts:
                # Generate natural language variations
                phrases = [
                    f"Swap {amount} {route.from_token} for {route.to_token}",
                    f"Trade {amount} {route.from_token} to {route.to_token}",
                    f"Convert {amount} {route.from_token} to {route.to_token}",
                ]
                
                for phrase in phrases:
                    example = {
                        "input": phrase,
                        "intent": {
                            "action": "swap",
                            "amount": amount,
                            "from_variant": route.from_token,
                            "to_variant": route.to_token,
                        },
                        "route": asdict(route),
                        "execution_steps": route.steps,
                        "user_preferences": {
                            "cheapest": route.total_cost_hbar,
                            "visible": route.hashpack_visible,
                            "auto_threshold": 0.05
                        },
                        "success_probability": route.complexity
                    }
                    training_examples.append(example)
        
        with open(output_path / "ultimate_training_examples.jsonl", "w") as f:
            for ex in training_examples:
                f.write(json.dumps(ex) + "\n")
        
        # 3. Simple lookup table
        lookup = {}
        for route in self.routes:
            key = f"{route.from_token}->{route.to_token}"
            if key not in lookup or route.total_cost_hbar < lookup[key]["cost"]:
                lookup[key] = {
                    "route_id": route.route_id,
                    "path": route.path,
                    "steps": route.steps,
                    "cost": route.total_cost_hbar,
                    "hashpack_visible": route.hashpack_visible,
                    "requires_wrap": route.requires_wrap_unwrap
                }
        
        with open(output_path / "ultimate_lookup.json", "w") as f:
            json.dump(lookup, f, indent=2)
        
        # 4. Statistics
        stats = {
            "total_routes": len(self.routes),
            "simple": len([r for r in self.routes if r.complexity == "SIMPLE"]),
            "medium": len([r for r in self.routes if r.complexity == "MEDIUM"]),
            "complex": len([r for r in self.routes if r.complexity == "COMPLEX"]),
            "hashpack_visible": len([r for r in self.routes if r.hashpack_visible]),
            "requires_wrap_unwrap": len([r for r in self.routes if r.requires_wrap_unwrap]),
            "training_examples": len(training_examples)
        }
        
        with open(output_path / "stats.json", "w") as f:
            json.dump(stats, f, indent=2)
        
        print(f"\n✅ Exported training data to {output_path}/")
        print(f"   • ultimate_matrix.json: {len(self.routes)} routes")
        print(f"   • ultimate_training_examples.jsonl: {len(training_examples)} examples")
        print(f"   • ultimate_lookup.json: {len(lookup)} optimized routes")
        
        return stats

def main():
    print("="*80)
    print("🧠 PACMAN ULTIMATE MATRIX BUILDER")
    print("="*80)
    
    matrix = PacmanUltimateMatrix()
    matrix.load_pools()
    matrix.build_matrix(amount_usd=100)
    stats = matrix.export_training_data()
    
    print(f"\n📊 Matrix Complete!")
    print(f"   Total Routes: {stats['total_routes']}")
    print(f"   Simple: {stats['simple']} | Medium: {stats['medium']} | Complex: {stats['complex']}")
    print(f"   HashPack Visible: {stats['hashpack_visible']}")
    print(f"   Requires Wrap/Unwrap: {stats['requires_wrap_unwrap']}")
    print(f"   Training Examples: {stats['training_examples']}")
    
    return 0

if __name__ == "__main__":
    exit(main())
