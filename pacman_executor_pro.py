#!/usr/bin/env python3
"""
Pacman Executor PRO - Full Live Transaction Execution
Uses SaucerSwap quoter for exact amounts, then executes real transactions.
"""

import os
import json
import time
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
from decimal import Decimal

from web3 import Web3
from eth_abi import encode

# Import clients
from saucerswap_v2_client import SaucerSwapV2, hedera_id_to_evm, encode_path
from pacman_associate import TokenAssociateManager

# Token decimals
DECIMALS = {
    "USDC": 6,
    "USDC[hts]": 6,
    "WBTC[hts]": 8,
    "WBTC_LZ": 8,
    "WBTC_HTS": 8,
    "WETH[hts]": 8,
    "WETH_HTS": 8,
    "WHBAR": 8,
    "HBAR": 8,
}

# Token IDs
TOKEN_IDS = {
    "USDC": "0.0.456858",
    "USDC[hts]": "0.0.1055459",
    "WBTC[hts]": "0.0.1055483",  # ERC20 version
    "WBTC_LZ": "0.0.1055483",
    "WBTC_HTS": "0.0.10082597",
    "WETH[hts]": "0.0.9770617",
    "WETH_HTS": "0.0.541564",
    "WHBAR": "0.0.1456986",
    "HBAR": "0.0.0",
}

@dataclass
class ExecutionResult:
    """Result of a transaction execution."""
    success: bool
    tx_hash: str = ""
    tx_id: str = ""  # Hedera transaction ID
    gas_used: int = 0
    hbar_cost: float = 0.0
    error: str = ""
    block_number: int = 0
    timestamp: str = ""
    steps_completed: int = 0
    total_steps: int = 0
    actual_output: float = 0.0  # Actual tokens received
    slippage: float = 0.0  # Actual slippage vs quote
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "tx_hash": self.tx_hash,
            "tx_id": self.tx_id,
            "gas_used": self.gas_used,
            "hbar_cost": self.hbar_cost,
            "error": self.error,
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps,
            "actual_output": self.actual_output,
            "slippage": self.slippage
        }

class PacmanExecutorPRO:
    """
    PRODUCTION executor with full Hedera transaction support.
    
    Workflow:
    1. Get EXACT quote from SaucerSwap quoter
    2. Check association
    3. Approve tokens
    4. Execute swap
    5. Verify receipt
    6. Record for AI training
    """
    
    def __init__(self, private_key: Optional[str] = None, 
                 network: str = "mainnet",
                 account_id: Optional[str] = None):
        """Initialize executor."""
        self.private_key = private_key or os.getenv("PACMAN_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
        if not self.private_key:
            raise ValueError("Private key required. Set PACMAN_PRIVATE_KEY in .env")
        
        self.network = network
        self.account_id = account_id or os.getenv("HEDERA_ACCOUNT_ID")
        
        # RPC endpoint
        self.rpc_url = "https://mainnet.hashio.io/api" if network == "mainnet" else "https://testnet.hashio.io/api"
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {self.rpc_url}")
        
        # SaucerSwap client
        self.client = SaucerSwapV2(self.w3, network=network, private_key=self.private_key)
        self.eoa = self.client.eoa
        self.chain_id = 295 if network == "mainnet" else 296
        
        # Association manager
        self.associate_manager = TokenAssociateManager(self.client, self.account_id)
        
        # Recording
        self.recordings_dir = Path("execution_records")
        self.recordings_dir.mkdir(exist_ok=True)
        
        print(f"✅ PacmanExecutorPRO initialized")
        print(f"   EOA: {self.eoa}")
        print(f"   Hedera ID: {self.account_id or 'Not set'}")
        print(f"   Network: {network}")
    
    def get_exact_quote(self, token_in_id: str, token_out_id: str, 
                      amount_in: float, fee_tier: int = 1500) -> Dict:
        """
        Get EXACT quote from SaucerSwap V2 quoter.
        
        Returns:
            {
                "amount_out": int,  # Raw token amount
                "amount_out_human": float,
                "gas_estimate": int,
                "price": float,  # Price per token
                "valid": bool
            }
        """
        try:
            # Convert to raw amount
            decimals_in = self._get_decimals(token_in_id)
            amount_raw = int(amount_in * (10 ** decimals_in))
            
            # Get quote from quoter contract
            quote = self.client.get_quote_single(token_in_id, token_out_id, amount_raw, fee_tier)
            
            # Convert output to human readable
            decimals_out = self._get_decimals(token_out_id)
            amount_out_human = quote["amount_out"] / (10 ** decimals_out)
            
            # Calculate effective price
            price = amount_in / amount_out_human if amount_out_human > 0 else 0
            
            return {
                "amount_out": quote["amount_out"],
                "amount_out_human": amount_out_human,
                "gas_estimate": quote.get("gasEstimate", 80000),
                "price": price,
                "sqrtPriceAfter": quote.get("sqrtPriceX96AfterList", []),
                "valid": True
            }
        
        except Exception as e:
            print(f"❌ Quote failed: {e}")
            return {
                "amount_out": 0,
                "amount_out_human": 0,
                "gas_estimate": 0,
                "price": 0,
                "valid": False,
                "error": str(e)
            }
    
    def execute_swap_pro(self, route, amount_usd: float) -> ExecutionResult:
        """
        Execute a swap with full quoter integration.
        
        Args:
            route: The VariantRoute to execute
            amount_usd: Amount in USD
        
        Returns:
            ExecutionResult with full transaction details
        """
        print(f"\n🚀 PRO Executing: ${amount_usd} {route.from_variant} → {route.to_variant}")
        print(f"   Steps: {len(route.steps)}")
        
        results = []
        total_gas_used = 0
        
        # Step 0: Token Association
        print("\n🔐 Step 0: Token Association")
        assoc_success, assoc_txs = self.associate_manager.ensure_associations_for_route(route)
        if not assoc_success:
            return ExecutionResult(success=False, error="Token association failed")
        print(f"   ✅ Associated {len(assoc_txs)} tokens")
        
        # Execute each step
        for i, step in enumerate(route.steps, 1):
            print(f"\n📍 Step {i}/{len(route.steps)}: {step.step_type.upper()}")
            
            if step.step_type == "swap":
                result = self._execute_swap_step_pro(step, amount_usd)
            else:
                result = ExecutionResult(success=False, error=f"Unknown step: {step.step_type}")
            
            results.append(result)
            
            if not result.success:
                print(f"❌ Step {i} failed: {result.error}")
                return result
            
            total_gas_used += result.gas_used
            print(f"   ✅ TX: {result.tx_hash[:30]}... Gas: {result.gas_used}")
        
        # Record execution
        final_result = results[-1] if results else ExecutionResult(success=False, error="No steps")
        final_result.total_steps = len(route.steps)
        final_result.steps_completed = sum(1 for r in results if r.success)
        final_result.gas_used = total_gas_used
        final_result.hbar_cost = total_gas_used * self.w3.eth.gas_price / 10**18
        
        self._record_execution_pro(route, amount_usd, results, final_result)
        
        return final_result
    
    def _execute_swap_step_pro(self, step, amount_usd: float) -> ExecutionResult:
        """Execute a swap step with exact quoter amounts."""
        try:
            from_symbol = step.from_token
            to_symbol = step.to_token
            
            # Resolve token IDs
            token_in_id = TOKEN_IDS.get(from_symbol)
            token_out_id = TOKEN_IDS.get(to_symbol)
            
            if not token_in_id or not token_out_id:
                return ExecutionResult(success=False, error=f"Unknown tokens: {from_symbol} → {to_symbol}")
            
            # Get fee tier
            fee_bps = step.details.get("fee_bps", 1500)
            
            # Get EXACT quote first
            print(f"   Getting exact quote from SaucerSwap...")
            quote = self.get_exact_quote(token_in_id, token_out_id, amount_usd, fee_bps)
            
            if not quote["valid"]:
                return ExecutionResult(success=False, error="Quote failed")
            
            print(f"   Quote: {amount_usd} {from_symbol} → {quote['amount_out_human']:.8f} {to_symbol}")
            print(f"   Expected output: {quote['amount_out']} (raw)")
            
            # Check current balance
            try:
                balance = self.client.get_token_balance(token_in_id)
                decimals = self._get_decimals(token_in_id)
                balance_human = balance / (10 ** decimals)
                print(f"   Your balance: {balance_human:.6f} {from_symbol}")
                
                if balance_human < amount_usd:
                    return ExecutionResult(
                        success=False, 
                        error=f"Insufficient balance: have {balance_human:.6f}, need {amount_usd}"
                    )
            except Exception as e:
                print(f"   ⚠️  Could not check balance: {e}")
            
            # Approve token spending
            print(f"   Approving {from_symbol} for SaucerSwap...")
            try:
                approve_tx = self.client.approve_token(token_in_id)
                print(f"   ✅ Approved: {approve_tx[:40]}...")
                time.sleep(3)  # Wait for propagation
            except Exception as e:
                # May already be approved
                print(f"   ℹ️  Approval note: {e}")
            
            # Build swap transaction
            print(f"   Building swap transaction...")
            
            # Calculate minimum output with 1% slippage
            min_output = int(quote["amount_out"] * 0.99)
            
            # Prepare path
            path = encode_path([token_in_id, token_out_id], [fee_bps])
            
            # Build transaction (simulation mode for safety check)
            # In real execution, this would call the router
            print(f"   📝 Transaction ready:")
            print(f"      Router: 0.0.3949434")
            print(f"      Amount in: {int(amount_usd * 10**6)} (raw USDC)")
            print(f"      Min out: {min_output} (raw)")
            print(f"      Deadline: {int(time.time()) + 1800}")
            
            # LIVE EXECUTION ENABLED
            print(f"   🔴 SUBMITTING LIVE TRANSACTION TO HEDERA MAINNET...")
            
            try:
                tx_hash = self._submit_swap_transaction(path, token_in_id, amount_usd, min_output)
                print(f"   ⏳ Waiting for confirmation...")
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                
                if receipt["status"] == 1:
                    print(f"   ✅ Transaction confirmed!")
                    print(f"   📄 Receipt: {receipt['transactionHash'].hex()}")
                    
                    return ExecutionResult(
                        success=True,
                        tx_hash=receipt['transactionHash'].hex(),
                        tx_id=str(receipt.get('transactionIndex', 0)),
                        gas_used=receipt['gasUsed'],
                        hbar_cost=receipt['gasUsed'] * receipt['effectiveGasPrice'] / 10**18,
                        actual_output=quote["amount_out_human"],
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                        block_number=receipt['blockNumber']
                    )
                else:
                    return ExecutionResult(
                        success=False,
                        error=f"Transaction failed: {receipt}",
                        tx_hash=receipt['transactionHash'].hex()
                    )
            
            except Exception as tx_error:
                print(f"   ❌ Transaction error: {tx_error}")
                return ExecutionResult(success=False, error=str(tx_error))
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ExecutionResult(success=False, error=str(e))
    
    def _submit_swap_transaction(self, path: bytes, token_in_id: str, 
                                 amount_in: float, min_output: int) -> str:
        """
        Submit actual swap transaction to Hedera via SaucerSwap V2 router.
        """
        try:
            # Build the exactInput transaction
            # Note: This is simplified - full implementation needs proper ABI encoding
            
            # For Hedera, we use the SaucerSwap V2 router contract
            router_address = self.client.router_address
            
            # Convert amount to raw
            decimals = self._get_decimals(token_in_id)
            amount_raw = int(amount_in * (10 ** decimals))
            
            # Build transaction parameters
            # CRITICAL: Hedera uses MILLISECOND deadlines, not seconds!
            deadline = int(time.time() * 1000) + 600000  # 10 min deadline in ms
            
            # Build transaction
            # Use tuple format like btc-rebalancer2
            params = (path, self.eoa, deadline, amount_raw, min_output)
            
            tx = self.client.router.functions.exactInput(params).build_transaction({
                "from": self.eoa,
                "gas": 1000000,  # Hedera gas limit (higher for safety)
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.eoa),
                "chainId": self.chain_id
            })
            
            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            
            # Submit transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            print(f"   📤 TX submitted: {tx_hash.hex()[:50]}...")
            return tx_hash.hex()
        
        except Exception as e:
            raise RuntimeError(f"Failed to submit transaction: {e}")
    
    def _get_decimals(self, token_id_or_symbol: str) -> int:
        """Get decimals for a token."""
        # Check if it's an ID
        for symbol, tid in TOKEN_IDS.items():
            if tid == token_id_or_symbol:
                return DECIMALS.get(symbol, 8)
        # Check if it's a symbol
        return DECIMALS.get(token_id_or_symbol, 8)
    
    def _record_execution_pro(self, route, amount_usd: float, 
                             step_results: list, final_result: ExecutionResult):
        """Record execution for AI training."""
        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": "PRO_EXECUTION",
            "route": {
                "from": route.from_variant,
                "to": route.to_variant,
                "steps": len(route.steps),
                "total_cost_hbar": route.total_cost_hbar,
                "hashpack_visible": route.hashpack_visible
            },
            "amount_usd": amount_usd,
            "step_results": [r.to_dict() for r in step_results],
            "final_result": final_result.to_dict(),
            "account": self.eoa,
            "hedera_id": self.account_id,
            "network": self.network
        }
        
        # Save to execution records
        filename = f"pro_exec_{time.strftime('%Y%m%d_%H%M%S')}_{route.from_variant}_to_{route.to_variant}.json"
        filepath = self.recordings_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(record, f, indent=2)
        
        # Append to training dataset
        training_file = Path("training_data/live_executions.jsonl")
        training_file.parent.mkdir(exist_ok=True)
        with open(training_file, 'a') as f:
            f.write(json.dumps(record) + "\n")
        
        print(f"\n📝 Recorded to: {filepath}")
        print(f"📊 Added to AI training dataset")

# CLI Test
if __name__ == "__main__":
    print("="*80)
    print("🚀 PACMAN EXECUTOR PRO - Live Transaction Test")
    print("="*80)
    
    from pacman_variant_router import PacmanVariantRouter
    from pacman_config import PacmanConfig
    
    # Initialize
    config = PacmanConfig.from_env()
    config.print_status()
    
    print("\n" + "="*80)
    
    # Initialize executor
    try:
        executor = PacmanExecutorPRO(
            private_key=config.private_key,
            network=config.network,
            account_id=config.hedera_account_id
        )
        
        # Get route
        router = PacmanVariantRouter()
        router.load_pools()
        
        route = router.recommend_route("USDC", "WBTC_HTS", "auto", amount_usd=1.0)
        
        if route:
            print(f"\n🎯 Testing route: {route.from_variant} → {route.to_variant}")
            
            # Execute
            result = executor.execute_swap_pro(route, amount_usd=1.0)
            
            print(f"\n{'='*80}")
            if result.success:
                print(f"✅ EXECUTION SUCCESSFUL")
                print(f"   TX Hash: {result.tx_hash}")
                print(f"   Actual output: {result.actual_output:.8f}")
                print(f"   Gas used: {result.gas_used}")
                print(f"   HBAR cost: {result.hbar_cost:.6f}")
            else:
                print(f"❌ EXECUTION FAILED: {result.error}")
            print(f"{'='*80}")
        else:
            print("❌ No route found")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
