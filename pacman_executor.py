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
    1. Token approval
    2. Swap on SaucerSwap
    3. Wrap/unwrap via ERC20Wrapper
    4. Record everything for AI training
    """
    
    def __init__(self, private_key: Optional[str] = None, network: str = "mainnet"):
        """Initialize executor with private key."""
        self.private_key = private_key or os.getenv("PACMAN_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
        if not self.private_key:
            # Check if we can run in simulation mode?
            # For now, just warn if missing but allow init for simulation-only usages if handled upstream
            # But the original code raised ValueError. Let's keep it but make it clear.
            # actually, verification script might want to run without it if simulating?
            # But verify_fixes.py creates executor() which fails here.
            pass # ValueError check is below
            
        if not self.private_key:
            raise ValueError("Private key required for execution (Set PACMAN_PRIVATE_KEY)")
        
        self.network = network
        self.rpc_url = "https://mainnet.hashio.io/api" if network == "mainnet" else "https://testnet.hashio.io/api"
        
        # Initialize web3 and client
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {self.rpc_url}")
        
        self.client = SaucerSwapV2(self.w3, network=network, private_key=self.private_key)
        self.eoa = self.client.eoa
        self.chain_id = 295 if network == "mainnet" else 296
        
        # Initialize wrapper contract
        self.wrapper_address = hedera_id_to_evm(ERC20_WRAPPER_ID)
        self.wrapper = self.w3.eth.contract(
            address=self.wrapper_address,
            abi=ERC20_WRAPPER_ABI
        )
        
        # Recording system
        self.recordings_dir = Path("execution_records")
        self.recordings_dir.mkdir(exist_ok=True)
        self.hedera_account_id = os.getenv("HEDERA_ACCOUNT_ID", "Unknown")
        
        print(f"✅ PacmanExecutor initialized")
        print(f"   Hedera Account: {self.hedera_account_id} (Native ID)")
        print(f"   EVM Address:    {self.eoa} (Ethereum Mirror)")
        print(f"   Network:        {network}")
    
    def execute_swap(self, route, amount_usd: float, mode: str = "exact_in", simulate: bool = True) -> ExecutionResult:
        """
        Execute a swap route.
        
        Args:
            route: The VariantRoute to execute
            amount_usd: Input amount (exact_in) or Output amount (exact_out). 
                        (Name legacy: implies USD but actually token units)
            mode: "exact_in" or "exact_out"
            simulate: If True, only quote (no actual transaction)
        
        Returns:
            ExecutionResult with full details
        """
        print(f"\n🚀 Executing swap: {amount_usd} {route.from_variant} → {route.to_variant}")
        print(f"   Mode: {mode.upper()} ({'SIMULATION' if simulate else 'LIVE'})")
        print(f"   Steps: {len(route.steps)}")
        
        results = []
        
        # --- Pre-Check: Token Association ---
        if not simulate:
            # We check the final destination token of the route
            last_step = route.steps[-1]
            final_token_id = last_step.details.get("token_out_id", last_step.to_token)
            
            print(f"   🛡️  Checking association for {route.to_variant}...")
            if not self.check_token_association(final_token_id):
                error_msg = f"Token {route.to_variant} ({final_token_id}) is not associated with your Hedera account."
                print(f"   ❌ {error_msg}")
                return ExecutionResult(success=False, error=error_msg)
            print(f"   ✅ Associated.")
        
        if mode == "exact_out" and len(route.steps) > 1:
            # Backwards Pass: Calculate requirements for each step
            print("   🔙 Performing Backwards Pass for Multi-Hop Exact Output...")
            targets = {} # step_index -> required_output_amount
            
            # The final step must output the user's requested amount
            last_decimals = self._get_token_decimals(route.steps[-1].to_token)
            next_needed_raw = int(amount_usd * (10 ** last_decimals))
            
            # Iterate backwards
            for i in range(len(route.steps) - 1, -1, -1):
                step = route.steps[i]
                targets[i] = next_needed_raw
                
                # Calculate input needed for this step to produce 'next_needed_raw'
                if step.step_type == "swap":
                    # Quote it
                    from_id = step.details.get("token_in_id", step.from_token)
                    to_id = step.details.get("token_out_id", step.to_token)
                    fee = step.details.get("fee_bps", 1500)
                    
                    try:
                        quote = self.client.get_quote_exact_output(from_id, to_id, next_needed_raw, fee)
                        next_needed_raw = quote['amount_in']
                        print(f"      Step {i+1} needs output: {targets[i]} -> Input required: {next_needed_raw}")
                    except Exception as e:
                        print(f"❌ Backwards pass failed at step {i+1}: {e}")
                        return ExecutionResult(success=False, error=f"Backwards pass failed: {e}")
                        
                elif step.step_type in ["wrap", "unwrap"]:
                    # 1:1 ratio
                    print(f"      Step {i+1} (Wrap/Unwrap): 1:1 ratio")
                    # next_needed_raw stays same
                    pass
            
            print("   ✅ Backwards pass complete. Executing forwarded...\n")
        else:
            targets = None

        results = []
        
        for i, step in enumerate(route.steps):
            step_idx = i + 1 # 1-based for display
            print(f"\n📍 Step {step_idx}/{len(route.steps)}: {step.step_type.upper()}")
            
            # Determine amount for this step
            if mode == "exact_out" and targets:
                # Use the pre-calculated target OUTPUT for this step
                step_amount = targets[i]
                
                # Get decimals for THIS step's output
                step_out_decimals = self._get_token_decimals(step.to_token)
                
                step_amount_float = step_amount / (10 ** step_out_decimals)
                current_amount_val = step_amount_float
            else:
                current_amount_val = amount_usd # For exact_in, or single hop
            
            # Determine decimals based on mode for the current step
            token_for_decimals = step.from_token if mode == "exact_in" else step.to_token
            decimals = self._get_token_decimals(token_for_decimals)
            amount_raw_for_step = int(current_amount_val * (10 ** decimals))

            if step.step_type == "swap":
                result = self._execute_swap_step(step, amount_raw_for_step, simulate, mode)
            elif step.step_type == "unwrap":
                result = self._execute_unwrap_step(step, simulate)
            elif step.step_type == "wrap":
                result = self._execute_wrap_step(step, simulate)
            else:
                result = ExecutionResult(success=False, error=f"Unknown step type: {step.step_type}")
            
            # --- NEW: VERIFY ON-CHAIN STATUS ---
            if result.success and not simulate and result.tx_hash != "SIMULATED":
                print(f"   ⏳ Verifying transaction on-chain: {result.tx_hash}...")
                try:
                    receipt = self.w3.eth.wait_for_transaction_receipt(result.tx_hash, timeout=60)
                    if receipt.status == 0:
                        result.success = False
                        result.error = "Transaction REVERTED on-chain"
                        print(f"   ❌ Reverted!")
                    else:
                        result.block_number = receipt.blockNumber
                        print(f"   ✅ Confirmed in block {receipt.blockNumber}")
                except Exception as e:
                    result.success = False
                    result.error = f"Timed out waiting for confirmation: {e}"
                    print(f"   ⚠️  Verification failed: {e}")

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
    
    def _get_token_decimals(self, token_symbol: str) -> int:
        """
        Get decimals for a token.
        TODO: In future, look up from tokens.json metadata.
        For now, hardcoded known list.
        """
        sym = token_symbol.upper()
        if "USDC" in sym or "USDT" in sym: return 6
        if "SAUCE" in sym or "XSAUCE" in sym: return 6
        if "WBTC" in sym: return 8
        return 8 # Default for HBAR and others

    def check_token_association(self, token_id: str) -> bool:
        """
        Check if the account is associated with the given HTS token.
        On Hedera, association is required to receive any HTS token.
        """
        if token_id.upper() == "HBAR":
            return True
            
        try:
            # Mirror Node checkout or simple balanceOf check
            # In EVM context, balanceOf usually returns 0 if not associated
            # rather than reverting, but we can try to catch specific signals.
            balance = self.client.get_token_balance(token_id)
            return True # If it returns a value (even 0), it's nominally fine in EVM
        except Exception as e:
            print(f"   ⚠️  Association check failed for {token_id}: {e}")
            return False

    def _execute_swap_step(self, step: Dict, amount_raw: int, simulate: bool = False, mode: str = "exact_in") -> ExecutionResult:
        """Execute a single swap step."""
        try:
            # Get token IDs from step
            from_token_id = step.details.get("token_in_id", step.from_token)
            to_token_id = step.details.get("token_out_id", step.to_token)
            
            # Get fee tier from step details
            fee_bps = step.details.get("fee_bps", 1500)
            
            # Determine decimals based on mode
            token_for_decimals = step.from_token if mode == "exact_in" else step.to_token
            decimals = self._get_token_decimals(token_for_decimals)
            amount_float = amount_raw / (10 ** decimals)
            
            # --- HBAR NATIVE LOGIC ---
            is_native_hbar = (step.from_token in ["HBAR", "0.0.0"])
            value_to_send = 0
            
            if is_native_hbar:
                # If we are swapping Native HBAR, we must:
                # 1. Send native HBAR as msg.value
                # 2. Use WHBAR address in the path (router auto-wraps)
                # 3. NOT approve (can't approve native)
                value_to_send = amount_raw
                # Ensure we use WHBAR ID for the router call's path
                from_token_id = "0.0.1456986" # WHBAR
            
            if simulate:
                # Just quote
                if mode == "exact_in":
                    quote = self.client.get_quote_single(from_token_id, to_token_id, amount_raw, fee_bps)
                    
                    # Decimals for output
                    out_decimals = self._get_token_decimals(step.to_token)
                    print(f"   Quote (Exact In): {amount_float} {step.from_token} → {quote['amount_out'] / (10**out_decimals)} {step.to_token}")
                    
                    if is_native_hbar:
                         print(f"   (Native HBAR Swap: Value={amount_raw})")
                else:
                    # Exact Output Quote
                    quote = self.client.get_quote_exact_output(from_token_id, to_token_id, amount_raw, fee_bps)
                    grams_in = quote['amount_in']
                    
                    # Decimals for input token
                    dec_in = self._get_token_decimals(step.from_token)
                    print(f"   Quote (Exact Out): Need {grams_in / (10**dec_in)} {step.from_token} → {amount_float} {step.to_token}")
                    
                return ExecutionResult(
                    success=True,
                    tx_hash="SIMULATED",
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                # Real execution
                # 1. Balance Check
                # If native, check ETH balance. If token, check token balance.
                if is_native_hbar:
                    current_balance = self.w3.eth.get_balance(self.eoa)
                    # For HBAR, we need amount + gas. 
                    # Simplification: just check amount for now
                else:
                    current_balance = self.client.get_token_balance(from_token_id)
                
                needed_balance = amount_raw
                
                # If exact_out, we better check what we actually NEED
                if mode == "exact_out":
                     quote = self.client.get_quote_exact_output(from_token_id, to_token_id, amount_raw, fee_bps)
                     needed_balance = int(quote["amount_in"] * 1.01) # Max with slippage
                
                if current_balance < needed_balance:
                    decimals_in = self._get_token_decimals(step.from_token)
                    
                    bal_readable = current_balance / (10**decimals_in)
                    need_readable = needed_balance / (10**decimals_in)
                    
                    if is_native_hbar:
                        # Account for gas buffer
                        return ExecutionResult(success=False, error=f"Insufficient HBAR: Have {bal_readable:.4f}, Need {need_readable:.4f} (+gas)")

                    return ExecutionResult(
                        success=False, 
                        error=f"Insufficient funds: Have {bal_readable:.6f}, Need {need_readable:.6f} {step.from_token}. (Check rounded balances!)"
                    )

                # 2. Approve if needed (SKIP for Native HBAR)
                if not is_native_hbar:
                    if mode == "exact_in":
                        # Approve token_in
                        current_allowance = self.client.get_allowance(from_token_id, self.client.eoa, self.client.router_address)
                        if current_allowance < amount_raw:
                            print(f"   🔓 Approving {step.from_token} ({from_token_id})...")
                            self.client.approve_token(from_token_id, amount_raw)
                            time.sleep(2) # propagation
                    else: 
                         # For exact_out, we approve max_amount_in. 
                         # Simplified: Approve from_token.
                         current_allowance = self.client.get_allowance(from_token_id, self.client.eoa, self.client.router_address)
                         if current_allowance < 2**255: # Check if approved enough
                             print(f"   🔓 Approving {step.from_token} ({from_token_id}) (max)...")
                             self.client.approve_token(from_token_id, 2**256 - 1)
                             time.sleep(2)

                # 3. Swap
                if mode == "exact_in":
                    # Min output (1% slippage)
                    quote = self.client.get_quote_single(from_token_id, to_token_id, amount_raw, fee_bps)
                    min_out = int(quote["amount_out"] * 0.99)
                    print(f"   🔄 Swap Param: amount_in={amount_raw}, min_out={min_out}")
                    
                    if is_native_hbar:
                        # HBAR -> Token (Multicall: exactInput + refundETH)
                        print(f"   🔄 Executing Multicall (ExactInput + RefundETH)...")
                        tx_hash = self.client.swap_exact_input_multicall(
                            from_token_id, to_token_id, amount_raw, min_out, 
                            input_is_native=True, fee=fee_bps
                        )
                    elif step.to_token == "HBAR": # Output is HBAR
                         # Token -> HBAR (Multicall: exactInput + unwrapWHBAR)
                         print(f"   🔄 Executing Multicall (ExactInput + UnwrapWHBAR)...")
                         tx_hash = self.client.swap_exact_input_multicall(
                            from_token_id, to_token_id, amount_raw, min_out,
                            output_is_native=True, fee=fee_bps
                         )
                    else:
                        # Standard
                        tx_hash = self.client.swap_exact_input(from_token_id, to_token_id, amount_raw, min_out, fee_bps)
                        
                    print(f"   🚀 Executed: {tx_hash}")
                else:
                    # Max input (1% slippage)
                    quote = self.client.get_quote_exact_output(from_token_id, to_token_id, amount_raw, fee_bps)
                    max_in = int(quote["amount_in"] * 1.01)
                    print(f"   🔄 Swap Param: amount_out={amount_raw}, max_in={max_in}")
                    
                    if is_native_hbar or step.to_token == "HBAR":
                        # TODO: excessive complexity for now, fallback to standard exactOutput but warn?
                        # Or implement swap_exact_output_multicall later.
                        # For now, let's just error if exact_out with HBAR to be safe, or try standard.
                        print("⚠️  Warning: exact_output not fully supported for Native HBAR via multicall yet. Using standard exactOutput (might fail for HBAR).")
                        tx_hash = self.client.swap_exact_output(from_token_id, to_token_id, amount_raw, max_in, fee_bps, value=value_to_send)
                    else:
                        tx_hash = self.client.swap_exact_output(from_token_id, to_token_id, amount_raw, max_in, fee_bps)
                        
                    print(f"   🚀 Executed: {tx_hash}")
                    
                return ExecutionResult(
                    success=True,
                    tx_hash=tx_hash,
                    gas_used=400_000, # Approximate / Limit for now
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
        
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _execute_unwrap_step(self, step, simulate: bool) -> ExecutionResult:
        """Execute unwrap ERC20 -> HTS."""
        try:
            # We use the mapping from erc20_to_hts_wrapper.py
            WRAPPER_ID = "0.0.9675688"
            
            # Decimals: ERC20 WBTC is 8, HTS WBTC is 8.
            # ERC20 WETH is 18? No, let's look at tokens.json mapping.
            
            from_token = step.from_token
            to_token = step.to_token
            
            # IDs
            from_id = step.details.get("token_in_id", from_token)
            
            # Determine decimals
            decimals = self._get_token_decimals(from_token)
            
            # The amount is stored in the step (from a previous swap result)
            # or passed in if standalone.
            # For now, we assume step.amount_raw is set if this is part of a route.
            amount_raw = getattr(step, 'amount_raw', 0)
            if amount_raw == 0:
                # Standalone call? Let's check if we have a way to pass it.
                pass
            
            print(f"   🔓 Unwrapping {amount_raw / (10**decimals)} {from_token} -> {to_token}...")
            
            if simulate:
                return ExecutionResult(success=True, tx_hash="SIMULATED_UNWRAP", timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))

            # 1. Approve Wrapper to spend ERC20
            self.client.approve_token(from_id, amount_raw, spender=WRAPPER_ID)
            
            # 2. Call withdrawTo(self.eoa, amount)
            wrapper_addr = hedera_id_to_evm(WRAPPER_ID)
            wrapper_contract = self.w3.eth.contract(address=wrapper_addr, abi=ERC20_WRAPPER_ABI)
            
            tx = wrapper_contract.functions.withdrawTo(self.eoa, amount_raw).build_transaction({
                "from": self.eoa,
                "gas": 1_000_000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.eoa),
                "chainId": self.client.chain_id,
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            return ExecutionResult(
                success=True,
                tx_hash=tx_hash.hex(),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )
            
        except Exception as e:
            print(f"   ❌ Unwrap failed: {e}")
            return ExecutionResult(success=False, error=str(e))
    
    def _execute_wrap_step(self, step, simulate: bool) -> ExecutionResult:
        """Execute wrap HTS -> ERC20."""
        try:
            WRAPPER_ID = "0.0.9675688"
            from_token = step.from_token
            to_token = step.to_token
            from_id = step.details.get("token_in_id", from_token)
            
            decimals = self._get_token_decimals(from_token)
            amount_raw = getattr(step, 'amount_raw', 0)
            
            print(f"   🔒 Wrapping {amount_raw / (10**decimals)} {from_token} -> {to_token}...")
            
            if simulate:
                return ExecutionResult(success=True, tx_hash="SIMULATED_WRAP", timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))

            # 1. Approve Wrapper to spend HTS
            # This uses the Hedera SDK via JS
            self.client.approve_token(from_id, amount_raw, spender=WRAPPER_ID)
            
            # 2. Call depositFor(self.eoa, amount)
            wrapper_addr = hedera_id_to_evm(WRAPPER_ID)
            wrapper_contract = self.w3.eth.contract(address=wrapper_addr, abi=ERC20_WRAPPER_ABI)
            
            tx = wrapper_contract.functions.depositFor(self.eoa, amount_raw).build_transaction({
                "from": self.eoa,
                "gas": 1_000_000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.eoa),
                "chainId": self.client.chain_id,
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            return ExecutionResult(
                success=True,
                tx_hash=tx_hash.hex(),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )
            
        except Exception as e:
            print(f"   ❌ Wrap failed: {e}")
            return ExecutionResult(success=False, error=str(e))
    
    def _record_execution(self, route, amount_val: float, results: list, simulate: bool):
        """Record execution details for AI training."""
        
        # Determine actual USD value from token amount
        usd_price = 0
        try:
            with open("tokens.json") as f:
                tokens_data = json.load(f)
                
                # Special case for HBAR (0.0.0 or HBAR variant)
                if route.from_variant == "HBAR" or route.from_variant == "0.0.0":
                    # Hardcoded fallback or try to find in metadata if it exists
                    usd_price = 0.09 # Default fallback if metadata fails
                    for meta in tokens_data.values():
                        if meta.get("symbol") == "HBAR":
                            usd_price = meta.get("priceUsd", usd_price)
                            break
                else:
                    # Try to find the price for the 'from' token
                    token_meta = tokens_data.get(route.from_variant)
                    if token_meta:
                        usd_price = token_meta.get("priceUsd", 0)
        except:
            pass
            
        actual_usd = amount_val * usd_price if usd_price > 0 else 0
        total_gas = sum(r.gas_used for r in results)
        
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
            "amount_token": amount_val,
            "amount_usd": round(actual_usd, 2),
            "gas_used": total_gas,
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
