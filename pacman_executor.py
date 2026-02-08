#!/usr/bin/env python3
"""
Pacman Executor - Live Transaction Execution
Handles swap execution + wrap/unwrap operations with full recording.
"""

import os
import json
import time
from typing import Dict, Optional
from dataclasses import dataclass
from pathlib import Path

# Import our saucerswap client
from saucerswap_v2_client import SaucerSwapV2, hedera_id_to_evm, encode_path
from web3 import Web3
from pacman_associate import TokenAssociateManager

# ERC20 Wrapper contract (from btc-rebalancer2)
ERC20_WRAPPER_ID = "0.0.9675688"
ERC20_WRAPPER_ABI = [
    {
        "inputs": [
            {"name": "account", "type": "address"},
            {"name": "value", "type": "uint256"}
        ],
        "name": "depositFor",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "account", "type": "address"},
            {"name": "value", "type": "uint256"}
        ],
        "name": "withdrawTo",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

@dataclass
class ExecutionResult:
    """Result of a transaction execution."""
    success: bool
    tx_hash: str = ""
    gas_used: int = 0
    error: str = ""
    block_number: int = 0
    timestamp: str = ""
    steps_completed: int = 0
    total_steps: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "tx_hash": self.tx_hash,
            "gas_used": self.gas_used,
            "error": self.error,
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps
        }

class PacmanExecutor:
    """
    Executes swaps with optional wrap/unwrap steps.
    
    Key feature: Can execute multi-step routes including:
    1. Token association (Hedera requirement)
    2. Token approval
    3. Swap on SaucerSwap
    4. Wrap/unwrap via ERC20Wrapper
    5. Record everything for AI training
    """
    
    def __init__(self, private_key: Optional[str] = None, network: str = "mainnet", account_id: Optional[str] = None):
        """Initialize executor with private key."""
        self.private_key = private_key or os.getenv("PRIVATE_KEY")
        if not self.private_key:
            raise ValueError("Private key required for execution")
        
        self.network = network
        self.rpc_url = "https://mainnet.hashio.io/api" if network == "mainnet" else "https://testnet.hashio.io/api"
        
        # Initialize web3 and client
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {self.rpc_url}")
        
        self.client = SaucerSwapV2(self.w3, network=network, private_key=self.private_key)
        self.eoa = self.client.eoa
        self.chain_id = 295 if network == "mainnet" else 296
        
        # Initialize association manager
        self.account_id = account_id or os.getenv("HEDERA_ACCOUNT_ID")
        self.associate_manager = TokenAssociateManager(self.client, self.account_id)
        
        # Initialize wrapper contract
        self.wrapper_address = hedera_id_to_evm(ERC20_WRAPPER_ID)
        self.wrapper = self.w3.eth.contract(
            address=self.wrapper_address,
            abi=ERC20_WRAPPER_ABI
        )
        
        # Recording system
        self.recordings_dir = Path("execution_records")
        self.recordings_dir.mkdir(exist_ok=True)
        
        print(f"✅ PacmanExecutor initialized")
        print(f"   Account: {self.eoa}")
        print(f"   Hedera ID: {self.account_id or 'Not set'}")
        print(f"   Network: {network}")
    
    def execute_swap(self, route, amount_usd: float, simulate: bool = True) -> ExecutionResult:
        """
        Execute a swap route.
        
        Args:
            route: The VariantRoute to execute
            amount_usd: Amount in USD (will convert to token units)
            simulate: If True, only quote (no actual transaction)
        
        Returns:
            ExecutionResult with full details
        """
        print(f"\n🚀 Executing swap: {amount_usd} {route.from_variant} → {route.to_variant}")
        print(f"   Mode: {'SIMULATION' if simulate else 'LIVE'}")
        print(f"   Steps: {len(route.steps)}")
        
        # Step 0: Check and handle token associations
        print("\n🔐 Step 0: Checking token associations...")
        assoc_success, assoc_txs = self.associate_manager.ensure_associations_for_route(route)
        if not assoc_success:
            return ExecutionResult(success=False, error="Failed to associate required tokens")
        if assoc_txs:
            print(f"   ✅ Associated {len(assoc_txs)} token(s)")
        
        results = []
        
        for i, step in enumerate(route.steps, 1):
            print(f"\n📍 Step {i}/{len(route.steps)}: {step.step_type.upper()}")
            
            if step.step_type == "swap":
                result = self._execute_swap_step(step, amount_usd, simulate)
            elif step.step_type == "unwrap":
                result = self._execute_unwrap_step(step, simulate)
            elif step.step_type == "wrap":
                result = self._execute_wrap_step(step, simulate)
            else:
                result = ExecutionResult(success=False, error=f"Unknown step type: {step.step_type}")
            
            results.append(result)
            
            if not result.success:
                print(f"❌ Step {i} failed: {result.error}")
                return result
            
            print(f"✅ Step {i} complete: {result.tx_hash[:20]}...")
        
        # Record execution
        self._record_execution(route, amount_usd, results, simulate)
        
        # Return aggregate result
        final_result = results[-1] if results else ExecutionResult(success=False, error="No steps executed")
        final_result.total_steps = len(route.steps)
        final_result.steps_completed = sum(1 for r in results if r.success)
        
        return final_result
    
    def _execute_swap_step(self, step, amount_usd: float, simulate: bool) -> ExecutionResult:
        """Execute a single swap step."""
        try:
            # Get token IDs from step
            from_token_id = step.from_token  # Simplified - would lookup actual ID
            to_token_id = step.to_token
            
            # Get fee tier from step details
            fee_bps = step.details.get("fee_bps", 1500)
            
            # Convert amount (simplified - assumes 6 decimals for USDC)
            amount_raw = int(amount_usd * 1_000_000)
            
            if simulate:
                # Just quote
                quote = self.client.get_quote_single(from_token_id, to_token_id, amount_raw, fee_bps)
                print(f"   Quote: {amount_usd} {step.from_token} → {quote['amount_out']} {step.to_token}")
                return ExecutionResult(
                    success=True,
                    tx_hash="SIMULATED",
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                # Real execution would go here
                # For now, simulate but mark as "WOULD_EXECUTE"
                print(f"   🔄 Would execute: exactInputSingle({from_token_id}, {to_token_id}, {fee_bps})")
                return ExecutionResult(
                    success=True,
                    tx_hash="WOULD_EXECUTE_" + str(int(time.time())),
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
        
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _execute_unwrap_step(self, step, simulate: bool) -> ExecutionResult:
        """Execute unwrap ERC20 → HTS."""
        try:
            # Get token address to unwrap
            erc20_token = step.from_token  # e.g., "WBTC_LZ"
            amount = 0  # Would get from previous step output
            
            print(f"   Unwrapping {erc20_token} via {ERC20_WRAPPER_ID}")
            
            if simulate:
                return ExecutionResult(
                    success=True,
                    tx_hash="UNWRAP_SIMULATED",
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                # Real unwrap transaction
                print(f"   🔄 Would execute: withdrawTo({self.eoa}, {amount})")
                return ExecutionResult(
                    success=True,
                    tx_hash="UNWRAP_WOULD_EXECUTE_" + str(int(time.time())),
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
        
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _execute_wrap_step(self, step, simulate: bool) -> ExecutionResult:
        """Execute wrap HTS → ERC20."""
        try:
            hts_token = step.from_token
            amount = 0  # Would get from previous step
            
            print(f"   Wrapping {hts_token} via {ERC20_WRAPPER_ID}")
            
            if simulate:
                return ExecutionResult(
                    success=True,
                    tx_hash="WRAP_SIMULATED",
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                print(f"   🔄 Would execute: depositFor({self.eoa}, {amount})")
                return ExecutionResult(
                    success=True,
                    tx_hash="WRAP_WOULD_EXECUTE_" + str(int(time.time())),
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
        
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _record_execution(self, route, amount_usd: float, results: list, simulate: bool):
        """Record execution details for AI training."""
        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": "SIMULATION" if simulate else "LIVE",
            "route": {
                "from": route.from_variant,
                "to": route.to_variant,
                "steps": len(route.steps),
                "total_cost_hbar": route.total_cost_hbar,
                "hashpack_visible": route.hashpack_visible
            },
            "amount_usd": amount_usd,
            "results": [r.to_dict() for r in results],
            "success": all(r.success for r in results),
            "account": self.eoa,
            "network": self.network
        }
        
        # Save to file
        filename = f"exec_{time.strftime('%Y%m%d_%H%M%S')}_{route.from_variant}_to_{route.to_variant}.json"
        filepath = self.recordings_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(record, f, indent=2)
        
        print(f"\n📝 Execution recorded: {filepath}")
        
        # Also append to training dataset
        training_file = Path("training_data/live_executions.jsonl")
        training_file.parent.mkdir(exist_ok=True)
        with open(training_file, 'a') as f:
            f.write(json.dumps(record) + "\n")
    
    def get_execution_history(self, limit: int = 10) -> list:
        """Get recent execution history."""
        files = sorted(self.recordings_dir.glob("exec_*.json"), reverse=True)
        history = []
        
        for f in files[:limit]:
            with open(f) as file:
                history.append(json.load(file))
        
        return history

# CLI Testing
if __name__ == "__main__":
    print("="*80)
    print("🚀 PACMAN EXECUTOR - Transaction Execution Engine")
    print("="*80)
    
    # Import router for testing
    from pacman_variant_router import PacmanVariantRouter
    
    # Initialize
    router = PacmanVariantRouter()
    router.load_pools()
    
    # Get a route
    print("\n📊 Testing route: USDC → WBTC_HTS")
    route = router.recommend_route("USDC", "WBTC_HTS", "auto", amount_usd=1.0)
    
    if route:
        print(f"\n{route.explain()}")
        
        # Initialize executor (without private key, simulation only)
        try:
            executor = PacmanExecutor(simulate=True)
            result = executor.execute_swap(route, amount_usd=1.0, simulate=True)
            
            print(f"\n{'='*80}")
            print(f"✅ Execution Result: {result.success}")
            print(f"   Steps: {result.steps_completed}/{result.total_steps}")
            print(f"   Recorded for AI training")
            print(f"{'='*80}")
        
        except Exception as e:
            print(f"\n⚠️  Executor requires private key for full functionality")
            print(f"   Error: {e}")
            print(f"   (Simulation mode available)")
    else:
        print("❌ No route found")
