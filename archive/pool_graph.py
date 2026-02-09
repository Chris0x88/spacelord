#!/usr/bin/env python3
"""
Pacman Pool Graph - 3-Hop Routing Engine
Builds connectivity graph from SaucerSwap V2 data for optimal path finding.
"""

import json
import networkx as nx
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PoolInfo:
    pool_id: int
    token_a_symbol: str
    token_a_id: str
    token_b_symbol: str
    token_b_id: str
    fee: int  # Fee in basis points (500 = 0.05%)
    liquidity: str
    amount_a: str
    amount_b: str
    price_impact_threshold: float = 0.05  # 5% max price impact

class PacmanPoolGraph:
    def __init__(self, pools_data_file: str = "pacman_data_raw.json"):
        self.graph = nx.Graph()
        self.pools: Dict[int, PoolInfo] = {}
        self.token_to_pools: Dict[str, List[int]] = {}
        
        if Path(pools_data_file).exists():
            self.load_pools_data(pools_data_file)
    
    def load_pools_data(self, pools_file: str):
        """Load and parse SaucerSwap V2 pools data."""
        with open(pools_file, 'r') as f:
            pools_raw = json.load(f)
        
        for pool_data in pools_raw:
            pool_info = PoolInfo(
                pool_id=pool_data["id"],
                token_a_symbol=pool_data["tokenA"]["symbol"],
                token_a_id=pool_data["tokenA"]["id"],
                token_b_symbol=pool_data["tokenB"]["symbol"],
                token_b_id=pool_data["tokenB"]["id"],
                fee=pool_data["fee"],
                liquidity=pool_data["liquidity"],
                amount_a=pool_data["amountA"],
                amount_b=pool_data["amountB"]
            )
            
            # Store pool info
            self.pools[pool_info.pool_id] = pool_info
            
            # Build token to pools mapping
            for token_symbol in [pool_info.token_a_symbol, pool_info.token_b_symbol]:
                if token_symbol not in self.token_to_pools:
                    self.token_to_pools[token_symbol] = []
                self.token_to_pools[token_symbol].append(pool_info.pool_id)
            
            # Add edge to graph with fee as weight
            self.graph.add_edge(
                pool_info.token_a_symbol,
                pool_info.token_b_symbol,
                weight=pool_info.fee / 10000,  # Convert to decimal
                pool_id=pool_info.pool_id,
                liquidity=float(pool_info.liquidity),
                fee_basis_points=pool_info.fee
            )
        
        print(f"Loaded {len(self.pools)} pools with {len(self.token_to_pools)} unique tokens")
    
    def find_optimal_path(self, token_from: str, token_to: str, max_hops: int = 3) -> Optional[Dict]:
        """
        Find the optimal trading path between two tokens.
        Returns path with total fees, expected slippage, and required contract calls.
        """
        if token_from not in self.graph or token_to not in self.graph:
            return None
        
        try:
            # Find all paths up to max_hops
            all_paths = list(nx.all_simple_paths(
                self.graph, token_from, token_to, cutoff=max_hops
            ))
            
            if not all_paths:
                return None
            
            # Score each path based on fees and liquidity
            best_path = None
            best_score = float('inf')
            
            for path in all_paths:
                path_analysis = self._analyze_path(path)
                
                # Scoring: lower is better (fees + liquidity penalty)
                score = path_analysis["total_fees"] + path_analysis["liquidity_penalty"]
                
                if score < best_score:
                    best_score = score
                    best_path = path_analysis
            
            return best_path
        
        except nx.NetworkXNoPath:
            return None
    
    def _analyze_path(self, path: List[str]) -> Dict:
        """Analyze a trading path for fees, liquidity, and execution requirements."""
        total_fees = 0.0
        liquidity_penalty = 0.0
        hops = []
        
        for i in range(len(path) - 1):
            token_a, token_b = path[i], path[i + 1]
            
            # Get edge data (pool information)
            edge_data = self.graph[token_a][token_b]
            pool_id = edge_data["pool_id"]
            pool_info = self.pools[pool_id]
            
            # Calculate fees (fix: fee is in basis points, convert correctly)
            hop_fee = edge_data["fee_basis_points"] / 10000  # 500 -> 0.005 (0.5%)
            total_fees += hop_fee
            
            # Calculate liquidity penalty (lower liquidity = higher penalty)
            liquidity = edge_data["liquidity"]
            if liquidity < 1000000:  # Less than 1M liquidity
                liquidity_penalty += 0.01  # 1% penalty
            elif liquidity < 10000000:  # Less than 10M liquidity
                liquidity_penalty += 0.005  # 0.5% penalty
            
            # Determine required contract function
            contract_function = self._determine_contract_function(
                token_a, token_b, pool_info
            )
            
            hop_info = {
                "pool_id": pool_id,
                "from_token": token_a,
                "to_token": token_b,
                "fee_percent": hop_fee * 100,
                "liquidity": liquidity,
                "contract_function": contract_function,
                "token_a_id": pool_info.token_a_id,
                "token_b_id": pool_info.token_b_id
            }
            
            hops.append(hop_info)
        
        return {
            "path": path,
            "num_hops": len(path) - 1,
            "total_fees": total_fees,
            "total_fees_percent": total_fees * 100,
            "liquidity_penalty": liquidity_penalty,
            "route_score": total_fees + liquidity_penalty,
            "hops": hops,
            "estimated_gas": self._estimate_gas(len(hops)),
            "complexity_level": "SIMPLE" if len(hops) == 1 else "MEDIUM" if len(hops) == 2 else "COMPLEX"
        }
    
    def _determine_contract_function(self, token_a: str, token_b: str, pool_info: PoolInfo) -> str:
        """Determine the correct contract function based on token types."""
        # This is simplified - real implementation would need to check:
        # - HTS vs ERC20 token types
        # - Whether tokens need association
        # - Wrapped vs unwrapped variants
        
        if "[hts]" in token_a.lower() and "[hts]" in token_b.lower():
            return "swapHTSforHTS"
        elif "[hts]" in token_a.lower():
            return "swapHTSforToken"
        elif "[hts]" in token_b.lower():
            return "swapTokenForHTS"
        else:
            return "swapExactTokensForTokens"
    
    def _estimate_gas(self, num_hops: int) -> str:
        """Estimate gas cost based on number of hops."""
        base_gas = 0.02  # Base 0.02 HBAR
        hop_gas = 0.015  # 0.015 HBAR per additional hop
        
        total_gas = base_gas + (num_hops * hop_gas)
        return f"{total_gas:.3f} HBAR"
    
    def get_token_connectivity(self, token: str) -> Dict:
        """Get all directly connected tokens and their pool information."""
        if token not in self.graph:
            return {}
        
        connections = {}
        for connected_token in self.graph[token]:
            edge_data = self.graph[token][connected_token]
            pool_info = self.pools[edge_data["pool_id"]]
            
            connections[connected_token] = {
                "pool_id": edge_data["pool_id"],
                "fee_percent": edge_data["weight"] * 100,
                "liquidity": edge_data["liquidity"],
                "pool_info": pool_info
            }
        
        return connections
    
    def find_arbitrage_opportunities(self, min_profit_percent: float = 0.1) -> List[Dict]:
        """Find potential arbitrage opportunities (3+ hop cycles)."""
        opportunities = []
        
        # Find cycles in the graph
        for node in self.graph.nodes():
            try:
                # Look for cycles of length 3-4
                for target in self.graph.nodes():
                    if node != target:
                        paths = list(nx.all_simple_paths(
                            self.graph, node, target, cutoff=3
                        ))
                        
                        for path in paths:
                            if len(path) >= 3:  # At least 3 hops for arbitrage
                                path_analysis = self._analyze_path(path + [node])  # Complete the cycle
                                
                                # Simple arbitrage check (this would need more sophisticated pricing)
                                if path_analysis["total_fees"] < min_profit_percent / 100:
                                    opportunities.append({
                                        "cycle": path + [node],
                                        "estimated_profit": min_profit_percent - (path_analysis["total_fees"] * 100),
                                        "path_analysis": path_analysis
                                    })
            except:
                continue
        
        return opportunities[:10]  # Return top 10 opportunities
    
    def export_training_graph(self) -> Dict:
        """Export graph data in format suitable for AI training."""
        training_data = {
            "tokens": list(self.graph.nodes()),
            "pools": {},
            "connections": {},
            "optimal_routes": {}
        }
        
        # Export pool data
        for pool_id, pool_info in self.pools.items():
            training_data["pools"][pool_id] = {
                "tokens": [pool_info.token_a_symbol, pool_info.token_b_symbol],
                "fee_basis_points": pool_info.fee,
                "liquidity": pool_info.liquidity,
                "token_ids": [pool_info.token_a_id, pool_info.token_b_id]
            }
        
        # Export connectivity matrix
        for token in self.graph.nodes():
            training_data["connections"][token] = list(self.graph[token].keys())
        
        # Pre-compute some optimal routes for training
        major_tokens = ["USDC", "USDC[hts]", "WBTC[hts]", "HBAR", "WETH[hts]"]
        for token_a in major_tokens:
            for token_b in major_tokens:
                if token_a != token_b and token_a in self.graph and token_b in self.graph:
                    optimal_path = self.find_optimal_path(token_a, token_b)
                    if optimal_path:
                        training_data["optimal_routes"][f"{token_a}->{token_b}"] = optimal_path
        
        return training_data


# Example usage and testing
if __name__ == "__main__":
    # Initialize the graph
    graph = PacmanPoolGraph()
    
    # Test path finding
    path = graph.find_optimal_path("USDC", "WBTC[hts]")
    if path:
        print(f"Optimal path from USDC to WBTC[hts]:")
        print(f"Route: {' -> '.join(path['path'])}")
        print(f"Total fees: {path['total_fees_percent']:.3f}%")
        print(f"Hops: {path['num_hops']}")
        print(f"Estimated gas: {path['estimated_gas']}")
        print("Hop details:")
        for i, hop in enumerate(path['hops']):
            print(f"  {i+1}. {hop['from_token']} -> {hop['to_token']} (Pool {hop['pool_id']}, {hop['fee_percent']:.2f}% fee)")
    
    # Export training data
    training_data = graph.export_training_graph()
    with open("workspace/trade-model-v1/training_graph_data.json", "w") as f:
        json.dump(training_data, f, indent=2)
    
    print(f"Exported training data with {len(training_data['optimal_routes'])} pre-computed routes")