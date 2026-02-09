#!/usr/bin/env python3
"""
Pacman Executor - Live Transaction Execution
Handles swap execution + wrap/unwrap operations with full recording.
"""

import os
import json
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
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
    """Result of a transaction execution with detailed receipt metadata."""
    success: bool
    tx_hash: str = ""
    gas_used: int = 0
    gas_price_hbar: float = 0.0
    gas_cost_hbar: float = 0.0
    error: str = ""
    block_number: int = 0
    timestamp: str = ""
    steps_completed: int = 0
    total_steps: int = 0
    
    # Receipt Metadata
    amount_in_raw: int = 0
    amount_out_raw: int = 0
    quoted_rate: float = 0.0
    effective_rate: float = 0.0
    gas_offered: int = 0
    account_id: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "tx_hash": self.tx_hash,
            "gas_used": self.gas_used,
            "gas_price_hbar": self.gas_price_hbar,
            "gas_cost_hbar": self.gas_cost_hbar,
            "error": self.error,
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps,
            "amount_in_raw": self.amount_in_raw,
            "amount_out_raw": self.amount_out_raw,
            "quoted_rate": self.quoted_rate,
            "effective_rate": self.effective_rate,
            "gas_offered": self.gas_offered,
            "account_id": self.account_id
        }

class PacmanExecutor:
    """
    Executes swaps with optional wrap/unwrap steps.
    
    Key feature: Can execute multi-step routes including:
    1. Token approval
    2. Swap on SaucerSwap (3 Engines: Standard, Native HBAR Multicall, Manual Convert)
    3. Recording everything for AI training (and professional receipts!)
    """
    
    def __init__(self, private_key: Optional[str] = None, network: str = "mainnet"):
        """Initialize executor with private key."""
        self.private_key = private_key or os.getenv("PACMAN_PRIVATE_KEY")
        if not self.private_key:
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
        self.chain_id = 146 if network == "mainnet" else 147 # Hedera Chain IDs
        
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
        """Execute a swap route."""
        print(f"\n🚀 Executing swap: {amount_usd} {route.from_variant} → {route.to_variant}")
        print(f"   Mode: {mode.upper()} ({'SIMULATION' if simulate else 'LIVE'})")
        print(f"   Steps: {len(route.steps)}")
        
        # --- Pre-Check: Token Association ---
        if not simulate:
            last_step = route.steps[-1]
            final_token_id = last_step.details.get("token_out_id", last_step.to_token)
            
            print(f"   🛡️  Checking association for {route.to_variant}...")
            if not self.check_token_association(final_token_id):
                error_msg = f"Token {route.to_variant} ({final_token_id}) is not associated with your Hedera account."
                print(f"   ❌ {error_msg}")
                return ExecutionResult(success=False, error=error_msg)
            print(f"   ✅ Associated.")
        
        if mode == "exact_out" and len(route.steps) > 1:
            print("   🔙 Performing Backwards Pass for Multi-Hop Exact Output...")
            targets = {} 
            last_decimals = self._get_token_decimals(route.steps[-1].to_token)
            next_needed_raw = int(amount_usd * (10 ** last_decimals))
            
            for i in range(len(route.steps) - 1, -1, -1):
                step = route.steps[i]
                targets[i] = next_needed_raw
                if step.step_type == "swap":
                    from_id = step.details.get("token_in_id", step.from_token)
                    to_id = step.details.get("token_out_id", step.to_token)
                    fee = step.details.get("fee_bps", 1500)
                    try:
                        quote = self.client.get_quote_exact_output(from_id, to_id, next_needed_raw, fee)
                        next_needed_raw = quote['amount_in']
                    except Exception as e:
                        return ExecutionResult(success=False, error=f"Backwards pass failed: {e}")
            print("   ✅ Backwards pass complete.\n")
        else:
            targets = None

        results = []
        for i, step in enumerate(route.steps):
            step_idx = i + 1
            print(f"\n📍 Step {step_idx}/{len(route.steps)}: {step.step_type.upper()}")
            
            if mode == "exact_out" and targets:
                step_amount = targets[i]
                step_out_decimals = self._get_token_decimals(step.to_token)
                current_amount_val = step_amount / (10 ** step_out_decimals)
            else:
                current_amount_val = amount_usd
            
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
            
            if result.success and not simulate and result.tx_hash != "SIMULATED":
                print(f"   ⏳ Verifying transaction on-chain: {result.tx_hash}...")
                try:
                    receipt = self.w3.eth.wait_for_transaction_receipt(result.tx_hash, timeout=60)
                    if receipt.status == 0:
                        result.success = False
                        result.error = "Transaction REVERTED on-chain"
                    else:
                        result.block_number = receipt.blockNumber
                        result.gas_used = receipt.gasUsed
                        
                        # Calculate gas cost in HBAR
                        # On Hedera Hashio, gasPrice is usually static or follows mirrored value.
                        # Receipt effectiveGasPrice is in tinybars? Or wei-tinybars?
                        # Hashio Relay uses 18 decimals for ETH compatibility.
                        tx_details = self.w3.eth.get_transaction(result.tx_hash)
                        eff_gas_price_wei = receipt.get('effectiveGasPrice', tx_details.get('gasPrice', 0))
                        
                        result.gas_price_hbar = eff_gas_price_wei / (10**18)
                        result.gas_cost_hbar = (result.gas_used * eff_gas_price_wei) / (10**18)
                        
                        # Calculate effective rate for this step if it's a swap
                        if step.step_type == "swap" and result.amount_in_raw > 0 and result.amount_out_raw > 0:
                            result.effective_rate = result.amount_out_raw / result.amount_in_raw

                except Exception as e:
                    result.success = False
                    result.error = f"Timed out: {e}"

            results.append(result)
            if not result.success:
                self._record_execution(route, amount_usd, results, simulate)
                return result
        
        self._record_execution(route, amount_usd, results, simulate)
        final_result = results[-1] if results else ExecutionResult(success=False, error="No steps")
        final_result.total_steps = len(route.steps)
        final_result.steps_completed = sum(1 for r in results if r.success)
        
        # Aggregate gas for the final result
        final_result.gas_used = sum(r.gas_used for r in results)
        final_result.gas_cost_hbar = sum(r.gas_cost_hbar for r in results)
        final_result.gas_offered = sum(r.gas_offered for r in results)
        final_result.account_id = self.hedera_account_id
        
        return final_result
    
    def _get_token_decimals(self, token_symbol: str) -> int:
        sym = token_symbol.upper()
        if "USDC" in sym or "USDT" in sym: return 6
        if "SAUCE" in sym or "XSAUCE" in sym: return 6
        if "WBTC" in sym: return 8
        return 8 # Default for HBAR 
    
    def check_token_association(self, token_id: str) -> bool:
        if token_id.upper() in ["HBAR", "0.0.0"]: return True
        try:
            balance = self.client.get_token_balance(token_id)
            return True 
        except Exception:
            return False

    def _execute_swap_step(self, step: dict, amount_raw: int, simulate: bool = False, mode: str = "exact_in") -> ExecutionResult:
        """Execute a single swap step using one of the three engines."""
        try:
            from_token_id = step.details.get("token_in_id", step.from_token)
            to_token_id = step.details.get("token_out_id", step.to_token)
            fee_bps = step.details.get("fee_bps", 1500)
            
            # Identify Engine A (Standard) vs Engine B (Native HBAR)
            is_native_hbar = (step.from_token.upper() in ["HBAR", "0.0.0"])
            
            # Get Quote for rate calculations
            if mode == "exact_in":
                # Engine will need amount_raw
                quote = self.client.get_quote_single(from_token_id if not is_native_hbar else "0.0.1456986", to_token_id, amount_raw, fee_bps)
                quoted_rate = quote['amount_out'] / amount_raw
                amount_in_expected = amount_raw
                amount_out_expected = quote['amount_out']
            else:
                # Engine will need amount_raw as amount_out
                quote = self.client.get_quote_exact_output(from_token_id if not is_native_hbar else "0.0.1456986", to_token_id, amount_raw, fee_bps)
                quoted_rate = amount_raw / quote['amount_in']
                amount_in_expected = quote['amount_in']
                amount_out_expected = amount_raw

            if simulate:
                return ExecutionResult(
                    success=True, 
                    tx_hash="SIMULATED", 
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    amount_in_raw=amount_in_expected,
                    amount_out_raw=amount_out_expected,
                    quoted_rate=quoted_rate,
                    effective_rate=quoted_rate, # No slippage/gas actuals in sim
                    gas_offered=1_000_000,
                    account_id=self.hedera_account_id
                )
            
            # Real execution
            if is_native_hbar:
                current_balance = self.w3.eth.get_balance(self.eoa)
            else:
                current_balance = self.client.get_token_balance(from_token_id)
            
            needed_balance = amount_in_expected
            if mode == "exact_out":
                 needed_balance = int(amount_in_expected * 1.01)
            
            if current_balance < needed_balance:
                return ExecutionResult(success=False, error=f"Insufficient funds")

            # Approve if needed
            if not is_native_hbar:
                current_allowance = self.client.get_allowance(from_token_id, self.client.eoa, self.client.router_address)
                if current_allowance < needed_balance:
                    print(f"   🔓 Approving {step.from_token}...")
                    self.client.approve_token(from_token_id, 2**256 - 1)
                    time.sleep(2)

            # Execution logic using proper engine
            if mode == "exact_in":
                min_out = int(amount_out_expected * 0.99)
                if is_native_hbar:
                    tx_hash = self.client.swap_exact_input_multicall(from_token_id, to_token_id, amount_raw, min_out, input_is_native=True, fee=fee_bps)
                elif step.to_token.upper() in ["HBAR", "0.0.0"]:
                    tx_hash = self.client.swap_exact_input_multicall(from_token_id, to_token_id, amount_raw, min_out, output_is_native=True, fee=fee_bps)
                else:
                    tx_hash = self.client.swap_exact_input(from_token_id, to_token_id, amount_raw, min_out, fee_bps)
            else:
                max_in = int(amount_in_expected * 1.01)
                if is_native_hbar or step.to_token.upper() in ["HBAR", "0.0.0"]:
                    tx_hash = self.client.swap_exact_output_multicall(
                        from_token_id, to_token_id, amount_raw, max_in,
                        input_is_native=is_native_hbar,
                        output_is_native=(step.to_token.upper() in ["HBAR", "0.0.0"]),
                        fee=fee_bps
                    )
                else:
                    tx_hash = self.client.swap_exact_output(from_token_id, to_token_id, amount_raw, max_in, fee_bps)
            
            return ExecutionResult(
                success=True, 
                tx_hash=tx_hash, 
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                amount_in_raw=amount_in_expected,
                amount_out_raw=amount_out_expected,
                quoted_rate=quoted_rate,
                gas_offered=1_000_000,
                account_id=self.hedera_account_id
            )
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _execute_unwrap_step(self, step, simulate: bool) -> ExecutionResult:
        try:
            WRAPPER_ID = "0.0.9675688"
            from_id = step.details.get("token_in_id", step.from_token)
            amount_raw = getattr(step, 'amount_raw', 0)
            if simulate: return ExecutionResult(success=True, tx_hash="SIMULATED_UNWRAP", amount_in_raw=amount_raw, amount_out_raw=amount_raw)
            self.client.approve_token(from_id, amount_raw, spender=WRAPPER_ID)
            wrapper_addr = hedera_id_to_evm(WRAPPER_ID)
            wrapper_contract = self.w3.eth.contract(address=wrapper_addr, abi=ERC20_WRAPPER_ABI)
            tx = wrapper_contract.functions.withdrawTo(self.eoa, amount_raw).build_transaction({
                "from": self.eoa, "gas": 1_000_000, "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.eoa), "chainId": self.client.chain_id,
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            return ExecutionResult(success=True, tx_hash=tx_hash.hex(), amount_in_raw=amount_raw, amount_out_raw=amount_raw)
        except Exception as e: return ExecutionResult(success=False, error=str(e))
    
    def _execute_wrap_step(self, step, simulate: bool) -> ExecutionResult:
        try:
            WRAPPER_ID = "0.0.9675688"
            from_id = step.details.get("token_in_id", step.from_token)
            amount_raw = getattr(step, 'amount_raw', 0)
            if simulate: return ExecutionResult(success=True, tx_hash="SIMULATED_WRAP", amount_in_raw=amount_raw, amount_out_raw=amount_raw)
            self.client.approve_token(from_id, amount_raw, spender=WRAPPER_ID)
            wrapper_addr = hedera_id_to_evm(WRAPPER_ID)
            wrapper_contract = self.w3.eth.contract(address=wrapper_addr, abi=ERC20_WRAPPER_ABI)
            tx = wrapper_contract.functions.depositFor(self.eoa, amount_raw).build_transaction({
                "from": self.eoa, "gas": 1_000_000, "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.eoa), "chainId": self.client.chain_id,
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            return ExecutionResult(success=True, tx_hash=tx_hash.hex(), amount_in_raw=amount_raw, amount_out_raw=amount_raw)
        except Exception as e: return ExecutionResult(success=False, error=str(e))
    
    def _record_execution(self, route, amount_val: float, results: list, simulate: bool):
        """Record execution details for AI training."""
        usd_price = 0
        try:
            with open("tokens.json") as f:
                tokens_data = json.load(f)
                if route.from_variant in ["HBAR", "0.0.0"]:
                    usd_price = 0.09 
                    for meta in tokens_data.values():
                        if meta.get("symbol") == "HBAR":
                            usd_price = meta.get("priceUsd", usd_price)
                            break
                else:
                    token_meta = tokens_data.get(route.from_variant)
                    if token_meta:
                        usd_price = token_meta.get("priceUsd", 0)
        except: pass
            
        actual_usd = amount_val * usd_price if usd_price > 0 else 0
        total_gas = sum(r.gas_used for r in results)
        total_gas_hbar = sum(r.gas_cost_hbar for r in results)
        
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
            "gas_cost_hbar": total_gas_hbar,
            "results": [r.to_dict() for r in results],
            "success": all(r.success for r in results),
            "account": self.eoa,
            "network": self.network
        }
        
        filename = f"exec_{time.strftime('%Y%m%d_%H%M%S')}_{route.from_variant}_to_{route.to_variant}.json"
        filepath = self.recordings_dir / filename
        with open(filepath, 'w') as f:
            json.dump(record, f, indent=2)
        
        print(f"\n📝 Execution recorded: {filepath}")
        
        training_file = Path("training_data/live_executions.jsonl")
        training_file.parent.mkdir(exist_ok=True)
        with open(training_file, 'a') as f:
            f.write(json.dumps(record) + "\n")
    
    def get_execution_history(self, limit: int = 10) -> list:
        if not self.recordings_dir.exists(): return []
        files = sorted(self.recordings_dir.glob("exec_*.json"), reverse=True)
        history = []
        for f in files[:limit]:
            try:
                with open(f) as file:
                    history.append(json.load(file))
            except: continue
        return history
