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
from pacman_logger import logger
from pacman_config import PacmanConfig
from pacman_errors import ConfigurationError, ExecutionError, InsufficientFundsError

# ERC20 Wrapper contract (from btc-rebalancer2)
ERC20_WRAPPER_ID = "0.0.9675688"
import json as _json
from pathlib import Path as _Path
ERC20_WRAPPER_ABI = _json.loads((_Path(__file__).parent / "abi" / "erc20_wrapper.json").read_text())

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
    gas_cost_usd: float = 0.0
    hbar_usd_price: float = 0.0
    
    # Fee Transparency
    lp_fee_amount: float = 0.0
    lp_fee_token: str = ""
    
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
            "account_id": self.account_id,
            "gas_cost_usd": self.gas_cost_usd,
            "hbar_usd_price": self.hbar_usd_price,
            "lp_fee_amount": self.lp_fee_amount,
            "lp_fee_token": self.lp_fee_token
        }

class PacmanExecutor:
    """
    Executes swaps with optional wrap/unwrap steps.
    """
    
    def __init__(self, config: PacmanConfig):
        """Initialize executor with configuration."""
        from saucerswap_v2_client import SaucerSwapV2, hedera_id_to_evm
        from web3 import Web3

        self.config = config
        
        # Ensure config is valid before proceeding
        try:
            self.config.validate()
        except ConfigurationError as e:
            if not self.config.simulate_mode:
                raise e # Re-raise if we are in live mode and config is bad
            # In sim mode, we might proceed with a dummy key if missing
            if not self.config.private_key:
                logger.warning("Simulation Mode: Using dummy private key.")
                self.config.private_key = "0x" + "0" * 64

        self.network = config.network
        self.rpc_url = config.rpc_url
        
        # Initialize web3 and client
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {self.rpc_url}")
        
        self.client = SaucerSwapV2(self.w3, network=self.network, private_key=self.config.private_key)
        self.eoa = self.client.eoa
        self.chain_id = 146 if self.network == "mainnet" else 147 # Hedera Chain IDs
        
        # Initialize wrapper contract
        self.wrapper_address = hedera_id_to_evm(ERC20_WRAPPER_ID)
        self.wrapper = self.w3.eth.contract(
            address=self.wrapper_address,
            abi=ERC20_WRAPPER_ABI
        )
        
        # Recording system
        self.recordings_dir = Path("execution_records")
        self.recordings_dir.mkdir(exist_ok=True)
        self.hedera_account_id = config.hedera_account_id or "Unknown"
        
        logger.info(f"✅ PacmanExecutor initialized")
        logger.info(f"   Hedera Account: {self.hedera_account_id} (Native ID)")
        logger.info(f"   EVM Address:    {self.eoa} (Ethereum Mirror)")
        logger.info(f"   Network:        {self.network}")

    def get_balances(self) -> Dict[str, float]:
        """Fetch all non-zero token balances for the account."""
        balances = {}
        
        # HBAR Balance
        hbar_bal = self.w3.eth.get_balance(self.eoa)
        hbar_readable = hbar_bal / (10**18)
        if hbar_readable > 0:
            balances["HBAR"] = hbar_readable
            
        # Token Balances from tokens.json
        try:
            tokens_path = os.path.join(os.path.dirname(__file__), "data/tokens.json")
            with open(tokens_path) as f:
                tokens_data = json.load(f)
                
            for sym, meta in tokens_data.items():
                token_id = meta.get("id")
                if not token_id: continue
                try:
                    raw_bal = self.client.get_token_balance(token_id)
                    if raw_bal > 0:
                        decimals = meta.get("decimals", 8)
                        balances[sym] = raw_bal / (10**decimals)
                except Exception as e:
                    logger.warning(f"Warning: Could not fetch balance for {sym} ({token_id}): {e}")
                    continue
        except Exception as e:
            logger.error(f"Error: Could not load tokens.json for balance check: {e}")
            
        return balances

    def _get_token_id(self, symbol: str) -> Optional[str]:
        """Convert symbol to token ID using tokens.json."""
        if symbol.startswith("0.0."):
            return symbol
        if symbol.upper() == "HBAR":
            return "0.0.0"
            
        try:
            tokens_path = os.path.join(os.path.dirname(__file__), "data/tokens.json")
            with open(tokens_path) as f:
                tokens_data = json.load(f)
            meta = tokens_data.get(symbol)
            if meta:
                return meta.get("id")
        except: pass
        return None

    def execute_swap(self, route, amount_usd: float, mode: str = "exact_in") -> ExecutionResult:
        """
        Execute a swap route consisting of one or more steps.
        """
        simulate = self.config.simulate_mode

        logger.info(f"\n🚀 Executing swap: {amount_usd} {route.from_variant} → {route.to_variant}")
        logger.info(f"   Mode: {mode.upper()} ({'SIMULATION' if simulate else 'LIVE'})")
        logger.info(f"   Steps: {len(route.steps)}")
        
        # 1. Association Check
        if not simulate:
            if not self._ensure_association(route):
                return ExecutionResult(success=False, error=f"Token association failed for {route.to_variant}")
        
        # 2. Backwards Pass (for Exact Output)
        targets = None
        if mode == "exact_out" and len(route.steps) > 1:
            targets = self._calculate_backwards_pass(route, amount_usd)
            if targets is None:
                return ExecutionResult(success=False, error="Backwards pass calculation failed")

        # 3. Execution Loop
        results = []
        current_amount_val = amount_usd

        for i, step in enumerate(route.steps):
            step_result, current_amount_val = self._process_step(
                i, step, route, mode, simulate, targets, current_amount_val
            )
            
            if not step_result.success:
                self._record_execution(route, amount_usd, results + [step_result], simulate)
                return step_result

            results.append(step_result)

        # 4. Finalize
        final_result = self._aggregate_results(results, route)
        self._record_execution(route, amount_usd, results, simulate)
        return final_result

    def _ensure_association(self, route) -> bool:
        """Ensure the target token is associated."""
        last_step = route.steps[-1]
        final_token_id = last_step.details.get("token_out_id", last_step.to_token)

        print(f"   🛡️  Checking association for {route.to_variant}...")
        if not self.check_token_association(final_token_id):
            logger.warning(f"   ⚠️  Token {route.to_variant} not associated. Attempting auto-association...")
            if self.associate_token(final_token_id):
                logger.info(f"   ✅ Auto-association successful.")
                time.sleep(2)
                return True
            else:
                logger.error(f"   ❌ Auto-association failed.")
                return False
        else:
            logger.info(f"   ✅ Associated.")
            return True

    def _calculate_backwards_pass(self, route, amount_out_usd: float) -> Optional[Dict[int, int]]:
        """Calculate required inputs for each step in a multi-hop exact output swap."""
        logger.info("   🔙 Performing Backwards Pass for Multi-Hop Exact Output...")
        targets = {}
        last_decimals = self._get_token_decimals(route.steps[-1].to_token)
        next_needed_raw = int(amount_out_usd * (10 ** last_decimals))

        try:
            for i in range(len(route.steps) - 1, -1, -1):
                step = route.steps[i]
                targets[i] = next_needed_raw
                if step.step_type == "swap":
                    from_id = step.details.get("token_in_id", step.from_token)
                    to_id = step.details.get("token_out_id", step.to_token)
                    fee = step.details.get("fee_bps", 1500)
                    quote = self.client.get_quote_exact_output(from_id, to_id, next_needed_raw, fee)
                    next_needed_raw = quote['amount_in']
            logger.info("   ✅ Backwards pass complete.\n")
            return targets
        except Exception as e:
            logger.error(f"Backwards pass failed: {e}")
            return None

    def _process_step(self, i: int, step, route, mode: str, simulate: bool, targets: Optional[dict], current_val: float):
        """Process a single step in the route."""
        step_idx = i + 1
        logger.info(f"\n📍 Step {step_idx}/{len(route.steps)}: {step.step_type.upper()}")
        
        if mode == "exact_out" and targets:
            step_amount = targets[i]
            step_out_decimals = self._get_token_decimals(step.to_token)
            current_step_input_val = step_amount / (10 ** step_out_decimals)
        else:
            current_step_input_val = current_val

        token_for_decimals = step.from_token if mode == "exact_in" else step.to_token
        decimals = self._get_token_decimals(token_for_decimals)
        amount_raw_for_step = int(current_step_input_val * (10 ** decimals))

        if step.step_type == "swap":
            result = self._execute_swap_step(step, amount_raw_for_step, simulate, mode)
        elif step.step_type == "unwrap":
            result = self._execute_unwrap_step(step, simulate)
        elif step.step_type == "wrap":
            result = self._execute_wrap_step(step, simulate)
        else:
            return ExecutionResult(success=False, error=f"Unknown step type: {step.step_type}"), current_val

        # Verify on-chain if live
        if result.success and not simulate and result.tx_hash != "SIMULATED":
            self._verify_transaction(result, step)

        # Update current value for next step (for exact_in)
        next_val = current_val
        if mode == "exact_in" and result.amount_out_raw > 0:
            to_decimals = self._get_token_decimals(step.to_token)
            next_val = result.amount_out_raw / (10 ** to_decimals)

        return result, next_val

    def _verify_transaction(self, result: ExecutionResult, step):
        """Wait for and verify transaction receipt."""
        logger.info(f"   ⏳ Verifying transaction on-chain: {result.tx_hash}...")
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(result.tx_hash, timeout=60)
            if receipt.status == 0:
                result.success = False
                result.error = "Transaction REVERTED on-chain"
            else:
                result.block_number = receipt.blockNumber
                result.gas_used = receipt.gasUsed

                tx_details = self.w3.eth.get_transaction(result.tx_hash)
                eff_gas_price_wei = receipt.get('effectiveGasPrice', tx_details.get('gasPrice', 0))

                result.gas_price_hbar = eff_gas_price_wei / (10**18)
                result.gas_cost_hbar = (result.gas_used * eff_gas_price_wei) / (10**18)

                result.hbar_usd_price = self._get_hbar_price_usd()
                result.gas_cost_usd = result.gas_cost_hbar * result.hbar_usd_price

                if step.step_type == "swap" and result.amount_in_raw > 0:
                    result.effective_rate = result.amount_out_raw / result.amount_in_raw
        except Exception as e:
            logger.error(f"   ❌ Verification failed: {e}")
            result.success = False
            result.error = f"Timed out: {e}"

    def _aggregate_results(self, results: List[ExecutionResult], route) -> ExecutionResult:
        """Combine multiple step results into a final report."""
        if not results:
            return ExecutionResult(success=False, error="No steps executed")

        final = results[-1]
        final.total_steps = len(route.steps)
        final.steps_completed = sum(1 for r in results if r.success)
        final.gas_used = sum(r.gas_used for r in results)
        final.gas_cost_hbar = sum(r.gas_cost_hbar for r in results)
        final.gas_offered = sum(r.gas_offered for r in results)
        final.account_id = self.hedera_account_id
        
        final.hbar_usd_price = self._get_hbar_price_usd()
        final.gas_cost_usd = final.gas_cost_hbar * final.hbar_usd_price
        
        return final
    
    def _get_hbar_price_usd(self) -> float:
        """Fetch current HBAR price in USD from PriceManager."""
        from pacman_price_manager import price_manager
        # Ensure it's loaded
        if price_manager.hbar_price == 0:
            price_manager.reload()
        return price_manager.get_hbar_price()

    
    def _get_token_decimals(self, token_symbol: str) -> int:
        sym = token_symbol.upper()
        # Handle variants explicitly
        if "USDC" in sym or "USDT" in sym: return 6
        if "SAUCE" in sym or "XSAUCE" in sym: return 6
        if "WBTC" in sym: return 8
        if "WETH" in sym: return 8
        return 8 # Default for HBAR 
    def check_token_association(self, token_id: str) -> bool:
        if token_id.upper() in ["HBAR", "0.0.0"]: return True
        try:
            balance = self.client.get_token_balance(token_id)
            return True 
        except Exception:
            return False

    def associate_token(self, token_id: str) -> bool:
        """Associate HTS token using the HTS Precompile."""
        if token_id.upper() in ["HBAR", "0.0.0"]: return True
        return self.client.associate_token_native(token_id)

    def _execute_swap_step(self, step: dict, amount_raw: int, simulate: bool = False, mode: str = "exact_in") -> ExecutionResult:
        """Execute a single swap step using one of the three engines."""
        try:
            from pacman_price_manager import price_manager
            hbar_price = price_manager.get_hbar_price()

            from_token_id = step.details.get("token_in_id", step.from_token)
            to_token_id = step.details.get("token_out_id", step.to_token)
            fee_bps = step.details.get("fee_bps", 3000)
            
            is_native_hbar = (step.from_token.upper() in ["HBAR", "0.0.0"])
            
            fee_percent = fee_bps / 1_000_000.0
            lp_fee_raw = int(amount_raw * fee_percent)
            decimals = self._get_token_decimals(step.from_token)
            lp_fee_val = lp_fee_raw / (10**decimals)
            
            if mode == "exact_in":
                quote = self.client.get_quote_single(from_token_id if not is_native_hbar else "0.0.1456986", to_token_id, amount_raw, fee_bps)
                quoted_rate = quote['amount_out'] / amount_raw
                amount_in_expected = amount_raw
                amount_out_expected = quote['amount_out']
            else:
                quote = self.client.get_quote_exact_output(from_token_id if not is_native_hbar else "0.0.1456986", to_token_id, amount_raw, fee_bps)
                quoted_rate = amount_raw / quote['amount_in']
                amount_in_expected = quote['amount_in']
                amount_out_expected = amount_raw

            if simulate:
                sim_gas_used = 150_000 
                sim_gas_cost_hbar = sim_gas_used * 0.00000085
                
                return ExecutionResult(
                    success=True, 
                    tx_hash="SIMULATED", 
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    amount_in_raw=amount_in_expected,
                    amount_out_raw=amount_out_expected,
                    quoted_rate=quoted_rate,
                    effective_rate=quoted_rate,
                    gas_offered=1_000_000,
                    gas_used=sim_gas_used,
                    gas_price_hbar=0.00000085,
                    gas_cost_hbar=sim_gas_cost_hbar,
                    account_id=self.hedera_account_id,
                    lp_fee_amount=lp_fee_val,
                    lp_fee_token=step.from_token,
                    hbar_usd_price=hbar_price,
                    gas_cost_usd=sim_gas_cost_hbar * hbar_price
                )
            
            if is_native_hbar:
                current_balance = self.w3.eth.get_balance(self.eoa)
            else:
                current_balance = self.client.get_token_balance(from_token_id)
            
            needed_balance = amount_in_expected
            if mode == "exact_out":
                 needed_balance = int(amount_in_expected * 1.01)
            
            if current_balance < needed_balance:
                # RAISE EXCEPTION instead of returning fail
                raise InsufficientFundsError(f"Insufficient funds: Have {current_balance}, Need {needed_balance}")

            if not is_native_hbar:
                current_allowance = self.client.get_allowance(from_token_id, self.client.eoa, self.client.router_address)
                if current_allowance < needed_balance:
                    logger.info(f"   🔓 Approving {step.from_token}...")
                    safe_approval = max(needed_balance * 100, current_balance)
                    self.client.approve_token(from_token_id, int(safe_approval))
                    time.sleep(2)

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
            
            gas_cost_hbar = 0.0
            gas_used = 0
            if not simulate:
                try:
                    logger.info(f"   ⏳ Waiting for on-chain confirmation...")
                    receipt = self.client.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                    gas_used = receipt['gasUsed']
                    effective_gas_price = receipt.get('effectiveGasPrice', self.client.w3.eth.gas_price)
                    gas_cost_hbar = (gas_used * effective_gas_price) / 100_000_000.0
                    logger.info(f"   ✅ Confirmed! Cost: {gas_cost_hbar:.8f} HBAR ({gas_used} gas)")
                except Exception as e:
                    logger.warning(f"   ⚠️ Could not fetch receipt stats: {e}")
            
            return ExecutionResult(
                success=True, 
                tx_hash=tx_hash, 
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                amount_in_raw=amount_in_expected,
                amount_out_raw=amount_out_expected,
                quoted_rate=quoted_rate,
                effective_rate=quoted_rate,
                gas_offered=sim_gas_used if simulate else 1_000_000,
                gas_used=sim_gas_used if simulate else gas_used,
                gas_cost_hbar=gas_cost_hbar,
                account_id=self.hedera_account_id,
                lp_fee_amount=lp_fee_val,
                lp_fee_token=step.from_token,
                hbar_usd_price=hbar_price,
                gas_cost_usd=gas_cost_hbar * hbar_price
            )
        except InsufficientFundsError as e:
            return ExecutionResult(success=False, error=str(e))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _execute_unwrap_step(self, step, simulate: bool) -> ExecutionResult:
        try:
            WRAPPER_ID = "0.0.9675688"
            from_id = step.details.get("token_in_id", step.from_token)
            amount_raw = getattr(step, 'amount_raw', 0)
            if simulate: return ExecutionResult(success=True, tx_hash="SIMULATED_UNWRAP", amount_in_raw=amount_raw, amount_out_raw=amount_raw)
            from saucerswap_v2_client import hedera_id_to_evm
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
            from saucerswap_v2_client import hedera_id_to_evm
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
        # Use centralized PriceManager (Phase 32)
        from pacman_price_manager import price_manager
        
        # Determine Price
        if route.from_variant in ["HBAR", "0.0.0"]:
            usd_price = price_manager.get_hbar_price()
            decimals = 8
        else:
            # We need to resolve the ID from the variant to get the price
            # route.from_variant is likely a symbol (e.g. USDC[hts]) or ID?
            # Router typically ensures route object has details. 
            # But here `route` is a VariantRoute object
            
            # Helper to find ID from Symbol if needed, similar to CLI
            # But let's check if the route object has the ID.
            # PacmanVariantRouter._get_token_meta() returns dict with ID.
            # But we don't have that here easily without reloading or hacking.
            
            # Let's rely on the Executor's _get_token_decimals for decimals
            decimals = self._get_token_decimals(route.from_variant)
            
            # For price, we try to lookup by Symbol if ID fails, but PriceManager expects ID.
            # We previously loaded tokens.json to bridge this.
            # Let's load tokens.json ONLY for Symbol->ID mapping.
            token_id = route.from_variant # Attempt to use as ID if it is one
            
            try:
                with open("data/tokens.json") as f:
                    tdata = json.load(f)
                    meta = tdata.get(route.from_variant)
                    if meta:
                        token_id = meta.get("id", token_id)
            except: pass
            
            usd_price = price_manager.get_price(token_id)
            
        # Phase 33: Record both amounts for history
        actual_amount_token = amount_val
        if results and decimals > 0:
            raw_in = results[0].amount_in_raw
            if raw_in > 0:
                actual_amount_token = raw_in / (10 ** decimals)

        actual_to_amount_token = 0.0
        if results:
            to_decimals = self._get_token_decimals(route.to_variant)
            raw_out = results[-1].amount_out_raw
            if raw_out > 0 and to_decimals > 0:
                actual_to_amount_token = raw_out / (10 ** to_decimals)

        actual_usd = actual_amount_token * usd_price if usd_price > 0 else 0
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
            "amount_token": actual_amount_token,
            "to_amount_token": actual_to_amount_token,
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
        
        from pacman_logger import logger
        logger.info(f"\n📝 Execution recorded: {filepath}")
        
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
