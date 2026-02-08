#!/usr/bin/env python3
"""
Pacman Matrix Builder - Pre-compute ALL valid swap combinations
Generates the complete matrix of token->token routes that never changes.
Run weekly to catch new pools.
"""

import json
import itertools
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path

@dataclass
class SwapRoute:
    """A single swap route between two tokens."""
    token_from: str
    token_to: str
    path: List[str]  # [TokenA, TokenB] or [TokenA, USDC, TokenB]
    pools: List[int]  # Pool IDs used
    fee_tiers: List[int]  # Fee tier for each hop
    total_fee_bps: int  # Total fees in basis points (500 = 0.5%)
    gas_estimate: int  # Gas in tinybar
    route_type: str  # "DIRECT", "USDC_HOP", "COMPLEX"
    confidence: float  # 0.0-1.0, higher = more reliable route

@dataclass 
class TokenPair:
    """Information about a token pair."""
    token_a: str
    token_b: str
    direct_pool: Optional[int] = None
    direct_fee: Optional[int] = None
    best_route: Optional[SwapRoute] = None
    all_routes: List[SwapRoute] = None

    def __post_init__(self):
        if self.all_routes is None:
            self.all_routes = []

class PacmanMatrixBuilder:
    """Builds the complete routing matrix for all whitelisted tokens."""
    
    def __init__(self):
        self.pools_data = None
        self.tokens = set()
        self.direct_pools = {}  # (token_a, token_b) -> (pool_id, fee)
        self.routing_matrix = {}  # token_from -> token_to -> SwapRoute
        
        # Core stable tokens for routing
        self.ROUTING_HUBS = ["USDC", "USDC[hts]", "WHBAR", "HBAR"]
        
        # Featured tokens (from btc-rebalancer2 pattern)
        self.FEATURED_TOKENS = [
            "USDC", "WBTC[hts]", "WHBAR", "WETH[hts]", "SAUCE", 
            "USDT[hts]", "DAI[hts]", "LINK[hts]", "HBARX"
        ]
    
    def load_pools_data(self, pools_file: str = "pacman_data_raw.json"):
        """Load SaucerSwap V2 pools data."""
        with open(pools_file, 'r') as f:
            self.pools_data = json.load(f)
        
        print(f"Loaded {len(self.pools_data)} pools")
        
        # Extract all tokens and direct pools
        for pool in self.pools_data:
            token_a = pool["tokenA"]["symbol"]
            token_b = pool["tokenB"]["symbol"]
            pool_id = pool["id"]
            fee = pool["fee"]
            
            self.tokens.add(token_a)
            self.tokens.add(token_b)
            
            # Store direct pools (both directions)
            self.direct_pools[(token_a, token_b)] = (pool_id, fee)
            self.direct_pools[(token_b, token_a)] = (pool_id, fee)
        
        print(f"Found {len(self.tokens)} unique tokens")
        print(f"Found {len(self.direct_pools)//2} unique pools")
    
    def find_direct_route(self, token_from: str, token_to: str) -> Optional[SwapRoute]:
        """Check if there's a direct pool between two tokens."""
        if (token_from, token_to) in self.direct_pools:
            pool_id, fee = self.direct_pools[(token_from, token_to)]
            
            return SwapRoute(
                token_from=token_from,
                token_to=token_to,
                path=[token_from, token_to],
                pools=[pool_id],
                fee_tiers=[fee],
                total_fee_bps=fee,
                gas_estimate=20000,  # ~0.02 HBAR in tinybar
                route_type="DIRECT",
                confidence=1.0
            )
        return None
    
    def find_hub_route(self, token_from: str, token_to: str) -> Optional[SwapRoute]:
        """Find the best 2-hop route through a routing hub (USDC, WHBAR, etc.)."""
        best_route = None
        best_total_fee = float('inf')
        
        for hub in self.ROUTING_HUBS:
            # Skip if we're already routing to/from the hub
            if hub in [token_from, token_to]:
                continue
            
            # Check if both legs exist
            leg1 = self.direct_pools.get((token_from, hub))
            leg2 = self.direct_pools.get((hub, token_to))
            
            if leg1 and leg2:
                pool1, fee1 = leg1
                pool2, fee2 = leg2
                total_fee = fee1 + fee2
                
                if total_fee < best_total_fee:
                    best_total_fee = total_fee
                    best_route = SwapRoute(
                        token_from=token_from,
                        token_to=token_to,
                        path=[token_from, hub, token_to],
                        pools=[pool1, pool2],
                        fee_tiers=[fee1, fee2],
                        total_fee_bps=total_fee,
                        gas_estimate=35000,  # ~0.035 HBAR for 2 hops
                        route_type="USDC_HOP" if hub.startswith("USDC") else "HUB_ROUTE",
                        confidence=0.9
                    )
        
        return best_route
    
    def build_complete_matrix(self) -> Dict[str, Dict[str, SwapRoute]]:
        """Build the complete routing matrix for all token combinations."""
        
        # Focus on featured tokens for the matrix (keep it manageable)
        active_tokens = [t for t in self.FEATURED_TOKENS if t in self.tokens]
        print(f"Building matrix for {len(active_tokens)} featured tokens: {active_tokens}")
        
        matrix = {}
        total_pairs = len(active_tokens) * (len(active_tokens) - 1)  # Directional pairs
        processed = 0
        
        for token_from in active_tokens:
            matrix[token_from] = {}
            
            for token_to in active_tokens:
                if token_from == token_to:
                    continue
                
                processed += 1
                
                # 1. Try direct route first
                route = self.find_direct_route(token_from, token_to)
                
                # 2. If no direct route, try hub routing
                if not route:
                    route = self.find_hub_route(token_from, token_to)
                
                if route:
                    matrix[token_from][token_to] = route
                    fee_pct = route.total_fee_bps / 10000  # 500 = 0.05%
                    print(f"[{processed}/{total_pairs}] {token_from} → {token_to}: {route.route_type} ({fee_pct:.2f}%)")
                else:
                    print(f"[{processed}/{total_pairs}] {token_from} → {token_to}: NO ROUTE")
        
        self.routing_matrix = matrix
        return matrix
    
    def generate_training_dataset(self) -> List[Dict]:
        """Generate training examples for the AI model."""
        training_data = []
        
        for token_from, destinations in self.routing_matrix.items():
            for token_to, route in destinations.items():
                
                # Create natural language variations
                amounts = [100, 500, 1000, 2500, 5000]  # Common amounts
                
                for amount in amounts:
                    # Generate different phrasings of the same swap
                    variations = [
                        f"Swap {amount} {token_from} for {token_to}",
                        f"Trade {amount} {token_from} to {token_to}",
                        f"Convert {amount} {token_from} to {token_to}",
                        f"Exchange {amount} {token_from} for {token_to}",
                        f"Sell {amount} {token_from} buy {token_to}",
                    ]
                    
                    for phrase in variations:
                        training_example = {
                            "input": phrase,
                            "intent": {
                                "action": "swap",
                                "amount": amount,
                                "token_from": token_from,
                                "token_to": token_to
                            },
                            "expected_route": asdict(route),
                            "execution_signature": self._generate_execution_signature(route, amount),
                            "complexity_score": len(route.path) - 1,  # 0=direct, 1=2-hop, etc.
                        }
                        training_data.append(training_example)
        
        print(f"Generated {len(training_data)} training examples")
        return training_data
    
    def _generate_execution_signature(self, route: SwapRoute, amount: int) -> Dict:
        """Generate the exact contract calls needed for this route."""
        
        if route.route_type == "DIRECT":
            return {
                "function": "exactInputSingle",
                "params": {
                    "tokenIn": route.path[0],
                    "tokenOut": route.path[1], 
                    "fee": route.fee_tiers[0],
                    "amountIn": amount,
                    "recipient": "user_address",
                    "deadline": "block_timestamp + 1800",
                    "amountOutMinimum": "calculated_minimum"
                },
                "gas_estimate": route.gas_estimate,
                "contract": "0.0.3949434"  # SaucerSwap V2 Router
            }
        else:  # Multi-hop
            return {
                "function": "exactInput", 
                "params": {
                    "path": f"encoded_path({route.path}, {route.fee_tiers})",
                    "amountIn": amount,
                    "recipient": "user_address",
                    "deadline": "block_timestamp + 1800",
                    "amountOutMinimum": "calculated_minimum"
                },
                "gas_estimate": route.gas_estimate,
                "contract": "0.0.3949434"
            }
    
    def export_training_files(self, output_dir: str = "training_data"):
        """Export all training data to files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 1. Complete routing matrix
        with open(output_path / "routing_matrix.json", "w") as f:
            # Convert SwapRoute objects to dict for JSON serialization
            matrix_dict = {}
            for from_token, destinations in self.routing_matrix.items():
                matrix_dict[from_token] = {}
                for to_token, route in destinations.items():
                    matrix_dict[from_token][to_token] = asdict(route)
            
            json.dump(matrix_dict, f, indent=2)
        
        # 2. Training dataset for AI
        training_data = self.generate_training_dataset()
        with open(output_path / "ai_training_examples.jsonl", "w") as f:
            for example in training_data:
                f.write(json.dumps(example) + "\n")
        
        # 3. Simple lookup table for runtime
        simple_lookup = {}
        for from_token, destinations in self.routing_matrix.items():
            for to_token, route in destinations.items():
                key = f"{from_token}->{to_token}"
                simple_lookup[key] = {
                    "path": route.path,
                    "pools": route.pools,
                    "fee_tiers": route.fee_tiers,
                    "total_fee_bps": route.total_fee_bps,
                    "type": route.route_type
                }
        
        with open(output_path / "simple_lookup.json", "w") as f:
            json.dump(simple_lookup, f, indent=2)
        
        # 4. Statistics
        stats = {
            "total_tokens": len(self.tokens),
            "featured_tokens": len([t for t in self.FEATURED_TOKENS if t in self.tokens]),
            "total_routes": sum(len(dest) for dest in self.routing_matrix.values()),
            "direct_routes": sum(1 for from_token, destinations in self.routing_matrix.items() 
                               for to_token, route in destinations.items() 
                               if route.route_type == "DIRECT"),
            "hub_routes": sum(1 for from_token, destinations in self.routing_matrix.items() 
                             for to_token, route in destinations.items() 
                             if route.route_type != "DIRECT"),
            "training_examples": len(training_data)
        }
        
        with open(output_path / "stats.json", "w") as f:
            json.dump(stats, f, indent=2)
        
        print(f"\n🎯 Training data exported to {output_path}/")
        print(f"   • routing_matrix.json: Complete route mappings")
        print(f"   • ai_training_examples.jsonl: {stats['training_examples']} training examples")
        print(f"   • simple_lookup.json: Runtime lookup table")
        print(f"   • stats.json: Build statistics")
        
        return stats

def main():
    """Build the complete Pacman routing matrix."""
    print("🧠 Building Pacman Matrix - Complete Token Route Pre-computation")
    print("="*80)
    
    builder = PacmanMatrixBuilder()
    
    # Load pool data
    builder.load_pools_data()
    
    # Build complete matrix
    matrix = builder.build_complete_matrix()
    
    # Export training files
    stats = builder.export_training_files()
    
    print(f"\n✅ Matrix Complete!")
    print(f"   📊 {stats['total_routes']} routes mapped")
    print(f"   🎯 {stats['direct_routes']} direct, {stats['hub_routes']} via hub")
    print(f"   🧠 {stats['training_examples']} training examples generated")
    
    return 0

if __name__ == "__main__":
    exit(main())