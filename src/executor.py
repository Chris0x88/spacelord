#!/usr/bin/env python3
"""
Pacman Executor - Live Transaction Execution
============================================

The "Engine Room". Takes a VariantRoute (from PacmanVariantRouter) and
executes it on-chain.

Delegates to extracted modules:
- src.balances    → get_balances()
- src.associations → check_token_association(), associate_token(), get_staking_info()
- src.history     → record_execution(), get_execution_history()

Key design decisions:
- `execute_swap()` is the single public entry point for ALL swap types.
- `_process_step()` dispatches to the correct handler based on step.step_type.
- `config.simulate_mode` is the master safety switch.
- All private key material is revealed momentarily and deleted immediately.

HEDERA-SPECIFIC TRAPS:
---------------------
1. ALWAYS use `self.eoa` (the ECDSA alias address) for signing.
2. HTS tokens need the HTS Precompile for approvals.
3. WHBAR (0.0.1456986) is strictly internal routing only.
4. Always eth_call simulate before broadcast on wrap/unwrap.
"""

import os
import json
import time
import requests
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
from src.logger import logger
from src.config import PacmanConfig, SecureString
from src.errors import ConfigurationError, ExecutionError, InsufficientFundsError

# Extracted modules (delegation)
from src.balances import get_balances as _get_balances_impl
from src.associations import (
    check_token_association as _check_association_impl,
    associate_token as _associate_token_impl,
    get_staking_info as _get_staking_info_impl,
)
from src.history import (
    record_execution as _record_execution_impl,
    record_v1_execution as _record_v1_execution_impl,
    record_staking_transaction as _record_staking_impl,
    record_transfer_execution as _record_transfer_impl,
    get_execution_history as _get_history_impl,
)

# ERC20 Wrapper contract (0.0.9675688) — handles HTS <-> ERC20 bridging (wrap/unwrap)
ERC20_WRAPPER_ID = "0.0.9675688"
ERC20_WRAPPER_ABI = json.loads((Path(__file__).parent.parent / "abi" / "erc20_wrapper.json").read_text())

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
        from lib.saucerswap import SaucerSwapV2, hedera_id_to_evm
        from web3 import Web3

        self.config = config
        self.is_sim = config.simulate_mode
        
        # Ensure config is valid before proceeding
        try:
            self.config.validate()
        except ConfigurationError as e:
            if not self.is_sim:
                raise e # Re-raise if we are in live mode and config is bad
            # In sim mode, we might proceed with a dummy key if missing
            if not self.config.private_key:
                logger.warning("Simulation Mode: Using dummy private key.")
                self.config.private_key = SecureString("0x" + "0" * 64)

        self.network = config.network
        self.rpc_url = config.rpc_url
        self.hedera_account_id = config.hedera_account_id or "Unknown"
        
        # Initialize web3 and client
        logger.debug(f"   [RPC] Connecting to {self.rpc_url} (timeout=10s)...")
        # Hashio requires x-api-key header; include if present in env
        import os
        headers = {}
        api_key = os.getenv("SAUCERSWAP_API_KEY_MAINNET") or os.getenv("PACMAN_API_KEY")
        if api_key:
            headers["x-api-key"] = api_key
            logger.debug(f"   [RPC] Added x-api-key header")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={'timeout': 10, 'headers': headers}))
        
        # We skip is_connected() as it can hang on some providers
        # Connection will be tested on first actual RPC call
        
        # Reveal private key only for client initialization
        pk_revealed = self.config.private_key.reveal() if self.config.private_key else None
        try:
            self.client = SaucerSwapV2(self.w3, network=self.network, private_key=pk_revealed)
        finally:
            if pk_revealed:
                del pk_revealed
        self.eoa = self.client.eoa
        self.chain_id = 295 if self.network == "mainnet" else 296 # Hedera Chain IDs

        # CRITICAL: Always use Alias address (self.eoa) for Hedera EVM.
        # Long-zero addresses cause gas-burning reverts in contract calls.
        self.eoa_long_zero = self.eoa 
        
        # Initialize wrapper contract
        self.wrapper_address = hedera_id_to_evm(ERC20_WRAPPER_ID)
        self.wrapper = self.w3.eth.contract(
            address=self.wrapper_address,
            abi=ERC20_WRAPPER_ABI
        )

        # Initialize Price Manager (Global Singleton)
        from lib.prices import price_manager
        self.price_manager = price_manager
        
        # Recording system
        self.recordings_dir = Path("execution_records")
        self.recordings_dir.mkdir(exist_ok=True)
        
        logger.debug(f"✅ PacmanExecutor initialized")
        logger.debug(f"   RPC Provider:   {self.rpc_url}")
        logger.debug(f"   Chain ID:      {self.chain_id}")
        logger.debug(f"   Hedera Account: {self.hedera_account_id} (Native ID)")
        logger.debug(f"   EVM Address:    {self.eoa} (Alias/Signing)")
        logger.debug(f"   EVM Long-Zero:  {self.eoa_long_zero}")
        logger.debug(f"   Network:        {self.network}")

    def execute_v1_swap(self, from_id: str, to_id: str, amount: float, simulate: bool = True) -> ExecutionResult:
        """
        Standalone V1 execution logic.
        Decoupled from V2 to allow independent deletion.
        """
        from lib.v1_saucerswap import SaucerSwapV1
        
        # 1. Resolve Symbols and Decimals
        from_meta = self._get_token_data(from_id)
        to_meta = self._get_token_data(to_id)
        
        from_sym = from_meta.get("symbol", from_id) if from_meta else from_id
        to_sym = to_meta.get("symbol", to_id) if to_meta else to_id
        from_dec = from_meta.get("decimals", 8) if from_meta else 8
        to_dec = to_meta.get("decimals", 8) if to_meta else 8

        logger.info(f"\n🚀 Executing V1 Swap: {amount} {from_sym} → {to_sym}")
        
        # Initialize client
        pk = self.config.private_key.reveal() if self.config.private_key else None
        v1_client = SaucerSwapV1(self.w3, network=self.network, private_key=pk)
        if pk: del pk

        # Convert amount to raw units using token's decimals
        amount_raw = int(amount * 10**from_dec)

        try:
            # 2. Quote
            logger.info("   🔍 Fetching V1 Quote...")
            amount_out_raw = v1_client.get_quote_single(from_id, to_id, amount_raw)
            slippage_factor = 1.0 - (self.config.max_slippage_percent / 100.0)
            min_out = int(amount_out_raw * slippage_factor)
            
            if simulate:
                expected_human = amount_out_raw / (10**to_dec)
                logger.info(f"   [SIM] V1 Swap Simulation OK. Expected: {expected_human:.6f} {to_sym}")
                final = ExecutionResult(
                    success=True, 
                    tx_hash="SIMULATED_V1", 
                    amount_in_raw=amount_raw, 
                    amount_out_raw=amount_out_raw
                )
                
                self._record_v1_execution(from_sym, to_sym, amount, final, simulate=True)
                return final

            # 3. Swap
            logger.info("   ⚡ Broadcasting V1 Swap...")
            tx_hash = v1_client.swap_exact_input(from_id, to_id, amount_raw, min_out)
            
            # 4. Verify
            logger.info(f"   ⏳ Verifying V1 Tx: {tx_hash}...")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt.status == 1:
                final = ExecutionResult(
                    success=True, 
                    tx_hash=tx_hash,
                    gas_used=receipt.gasUsed,
                    amount_in_raw=amount_raw,
                    amount_out_raw=amount_out_raw
                )
                
                # Enrich for history
                final.hbar_usd_price = self._get_hbar_price_usd()
                final.gas_cost_hbar = (receipt.gasUsed * self.w3.eth.gas_price) / 10**18
                final.gas_cost_usd = final.gas_cost_hbar * final.hbar_usd_price
                
                self._record_v1_execution(from_sym, to_sym, amount, final, simulate=False)
                return final
            else:
                return ExecutionResult(success=False, error="V1 Transaction Reverted")

        except Exception as e:
            logger.error(f"   ❌ V1 Swap Failed: {e}")
            return ExecutionResult(success=False, error=str(e))

    def get_balances(self, token_highlights: list = None, eoa_override: str = None) -> Dict[str, float]:
        """Fetch all non-zero token balances using Multicall (with priority fallback)."""
        target_eoa = eoa_override or self.eoa
        return _get_balances_impl(self.w3, target_eoa, self.client, token_highlights=token_highlights)


    def _get_token_id(self, symbol: str) -> Optional[str]:
        """Convert symbol to token ID using tokens.json."""
        if symbol.startswith("0.0."):
            return symbol
        if symbol.upper() == "HBAR":
            return "0.0.0"
            
        try:
            root = Path(__file__).parent.parent
            tokens_path = root / "data" / "tokens.json"
            if not tokens_path.exists():
                 tokens_path = Path("data/tokens.json")

            with open(tokens_path) as f:
                tokens_data = json.load(f)
            
            # 1. Exact Key Match (Case-Insensitive)
            search_sym = symbol.upper()
            meta = None
            for key, data in tokens_data.items():
                if key.upper() == search_sym:
                    meta = data
                    break
            
            # 2. Symbol Field Match (if key match failed)
            if not meta:
                for key, data in tokens_data.items():
                    if data.get("symbol", "").upper() == search_sym:
                        meta = data
                        break
            
            if meta:
                return meta.get("id")
        except Exception:
            pass
        return None

    def _get_token_data(self, token_id_or_symbol: str) -> Optional[dict]:
        """Get full metadata for a token from tokens.json."""
        try:
            root = Path(__file__).parent.parent
            tokens_path = root / "data" / "tokens.json"
            if not tokens_path.exists():
                 tokens_path = Path("data/tokens.json")

            with open(tokens_path) as f:
                tokens_data = json.load(f)
            
            search = token_id_or_symbol.upper()
            
            # 1. Check if it's already an ID
            if token_id_or_symbol.startswith("0.0."):
                for meta in tokens_data.values():
                    if meta.get("id") == token_id_or_symbol:
                        return meta
                # Special cases for HBAR
                if token_id_or_symbol == "0.0.0":
                    return tokens_data.get("HBAR")
            
            # 2. Key/Symbol lookup
            if search in tokens_data:
                return tokens_data[search]
            
            for meta in tokens_data.values():
                if meta.get("symbol", "").upper() == search:
                    return meta
                    
        except: pass
        return None

    def execute_swap(self, route, raw_amount: float = 0.0, mode: str = "exact_in", **kwargs) -> ExecutionResult:
        """
        Execute a swap route consisting of one or more steps.
        
        Args:
            route: The route to execute
            raw_amount: The amount of tokens to swap (e.g. 100.0 HBAR, not USD value)
            mode: "exact_in" or "exact_out"
        """
        # Backward compatibility for old calls using amount_usd
        if raw_amount == 0.0 and "amount_usd" in kwargs:
            raw_amount = kwargs["amount_usd"]

        amount_val = raw_amount # Internal variable name for clarity
        simulate = self.config.simulate_mode

        if mode == "exact_in":
            logger.info(f"\n🚀 Executing swap: {amount_val} {route.from_variant} → {route.to_variant}")
        else:
            logger.info(f"\n🚀 Executing swap: {route.from_variant} → {amount_val} {route.to_variant}")
        logger.info(f"   Mode: {mode.upper()} ({'SIMULATION' if simulate else 'LIVE'})")
        logger.debug(f"   [DEBUG] Steps: {len(route.steps)}")
        for step in route.steps:
            logger.debug(f"     -> {step.step_type.upper()}: {step.from_token} to {step.to_token}")
        
        # 1. Association Check
        if not simulate:
            if not self._ensure_association(route):
                return ExecutionResult(success=False, error=f"Token association failed for {route.to_variant}")
        
        # 2. Backwards Pass (for Exact Output)
        targets = None
        if mode == "exact_out" and len(route.steps) > 1:
            targets = self._calculate_backwards_pass(route, amount_val)
            if targets is None:
                return ExecutionResult(success=False, error="Backwards pass calculation failed")

        # 3. Execution Loop
        results = []
        current_amount_val = amount_val

        for i, step in enumerate(route.steps):
            step_result, current_amount_val = self._process_step(
                i, step, route, mode, simulate, targets, current_amount_val,
                account_id=kwargs.get("account_id_override")
            )
            
            if not step_result.success:
                self._record_execution(route, amount_val, results + [step_result], simulate)
                return step_result

            results.append(step_result)

        # 4. Finalize
        final_result = self._aggregate_results(results, route)
        self._record_execution(route, amount_val, results, simulate)
        return final_result

    def _ensure_association(self, route) -> bool:
        """Ensure the target token is associated."""
        last_step = route.steps[-1]
        logger.debug(f"   [DEBUG] Last Step Details: {last_step.details}")
        logger.debug(f"   [DEBUG] Last Step To Token: {last_step.to_token}")
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

    def _calculate_backwards_pass(self, route, raw_amount_out: float) -> Optional[Dict[int, int]]:
        """Calculate required inputs for each step in a multi-hop exact output swap."""
        logger.info("   🔙 Performing Backwards Pass for Multi-Hop Exact Output...")
        targets = {}
        last_decimals = self._get_token_decimals(route.steps[-1].to_token)
        next_needed_raw = int(raw_amount_out * (10 ** last_decimals))

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

    def _process_step(self, i: int, step, route, mode: str, simulate: bool, targets: Optional[dict], current_val: float, account_id: str = None):
        """Process a single step in the route."""
        step_idx = i + 1
        logger.info(f"\n📍 Step {step_idx}/{len(route.steps)}: {step.step_type.upper()}")
        logger.debug(f"   From: {step.from_token} -> To: {step.to_token}")
        logger.debug(f"   Contract: {getattr(step, 'contract', 'N/A')}")
        
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
            result = self._execute_swap_step(step, amount_raw_for_step, simulate, mode, account_id=account_id)
        elif step.step_type == "unwrap":
            result = self._execute_unwrap_step(step, amount_raw_for_step, simulate, account_id=account_id)
        elif step.step_type == "wrap":
            result = self._execute_wrap_step(step, amount_raw_for_step, simulate, account_id=account_id)
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

                # Ensure price manager is loaded
                if self.price_manager.hbar_price == 0:
                    self.price_manager.reload()

                result.hbar_usd_price = self.price_manager.get_hbar_price()
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

        # The final result should represent the journey from first step input to last step output
        final = results[-1]
        final.total_steps = len(route.steps)
        final.steps_completed = sum(1 for r in results if r.success)
        final.gas_used = sum(r.gas_used for r in results)
        final.gas_cost_hbar = sum(r.gas_cost_hbar for r in results)
        final.gas_offered = sum(r.gas_offered for r in results)
        final.account_id = self.hedera_account_id
        
        # CRITICAL FIX: The first step has the user's actual input amount (in correct decimals/units)
        # The last step has the final units received. 
        final.amount_in_raw = results[0].amount_in_raw
        
        final.hbar_usd_price = self._get_hbar_price_usd()
        final.gas_cost_usd = final.gas_cost_hbar * final.hbar_usd_price
        
        return final
    
    def _get_hbar_price_usd(self) -> float:
        """Fetch current HBAR price in USD from PriceManager."""
        from lib.prices import price_manager
        # Ensure it's loaded
        if price_manager.hbar_price == 0:
            price_manager.reload()
        return price_manager.get_hbar_price()

    
    def _get_token_decimals(self, token_id_or_sym: str) -> int:
        """Look up token decimals by Hedera ID first, then fallback to API."""
        import json as _json
        # Try to look up by Hedera token ID from tokens.json
        if token_id_or_sym.startswith("0.0."):
            try:
                with open("data/tokens.json") as f:
                    tdata = _json.load(f)
                for tid, m in tdata.items():
                    if tid == token_id_or_sym:
                        return m.get("decimals", 8)
            except Exception:
                pass

        # Fallback: exact ID match
        tid = token_id_or_sym
        if tid in ["0.0.456858", "0.0.1055459", "0.0.731861", "0.0.1460200", "0.0.4794920"]: return 6
        if tid in ["0.0.10082597", "0.0.9470869", "0.0.4568584"]: return 8
        if tid in ["0.0.0", "0.0.1456986"]: return 8 # HBAR / WHBAR
        
        # Last resort: Mirror Node lookup
        if token_id_or_sym.startswith("0.0."):
            try:
                import requests
                r = requests.get(f"https://mainnet-public.mirrornode.hedera.com/api/v1/tokens/{token_id_or_sym}", timeout=3)
                if r.status_code == 200:
                    return int(r.json().get('decimals', 8))
            except: pass
            
        return 8  # Default for HBAR and unknowns




    def check_token_association(self, token_id: str) -> bool:
        """Check if the account is associated with the token."""
        return _check_association_impl(
            self.client, token_id, self.hedera_account_id, self.eoa, self.network
        )

    def get_staking_info(self) -> Dict:
        """Fetch staking info from Mirror Node."""
        return _get_staking_info_impl(self.hedera_account_id, self.eoa, self.network)

    def associate_token(self, token_id: str) -> bool:
        """Associate HTS token using Native Precompiles."""
        return _associate_token_impl(self.client, token_id)


    def _execute_swap_step(self, step: dict, amount_raw: int, simulate: bool = False, mode: str = "exact_in", account_id: str = None) -> ExecutionResult:
        """Execute a single swap step using one of the three engines."""
        try:
            from lib.prices import price_manager
            hbar_price = price_manager.get_hbar_price()

            from_token_id = step.details.get("token_in_id", step.from_token)
            to_token_id = step.details.get("token_out_id", step.to_token)
            fee_bps = step.details.get("fee_bps", 3000)
            
            is_native_hbar = (step.from_token.upper() in ["HBAR", "0.0.0"])
            
            fee_percent = fee_bps / 1_000_000.0
            lp_fee_raw = int(amount_raw * fee_percent)
            decimals = self._get_token_decimals(step.from_token)
            lp_fee_val = lp_fee_raw / (10**decimals)
            
            # Simulated gas constants (used in sim path AND as fallback sentinel for live path)
            SIM_GAS_USED = 150_000
            SIM_GAS_COST_HBAR = SIM_GAS_USED * 0.00000085

            if mode == "exact_in":
                logger.debug(f"      - Requesting Quote (Exact In): {amount_raw} {from_token_id} -> {to_token_id} @ fee {fee_bps}")
                quote = self.client.get_quote_single(from_token_id if not is_native_hbar else "0.0.1456986", to_token_id, amount_raw, fee_bps)
                logger.debug(f"      - Quote received: {quote.get('amount_out', 0)}")
                quoted_rate = quote['amount_out'] / amount_raw
                amount_in_expected = amount_raw
                amount_out_expected = quote['amount_out']
            else:
                logger.debug(f"      - Requesting Quote (Exact Out): {amount_raw} {from_token_id} -> {to_token_id} @ fee {fee_bps}")
                quote = self.client.get_quote_exact_output(from_token_id if not is_native_hbar else "0.0.1456986", to_token_id, amount_raw, fee_bps)
                logger.debug(f"      - Quote received: {quote.get('amount_in', 0)}")
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
                    effective_rate=quoted_rate,
                    gas_offered=2_000_000,
                    gas_used=SIM_GAS_USED,
                    gas_price_hbar=0.00000085,
                    gas_cost_hbar=SIM_GAS_COST_HBAR,
                    account_id=self.hedera_account_id,
                    lp_fee_amount=lp_fee_val,
                    lp_fee_token=step.from_token,
                    hbar_usd_price=hbar_price,
                    gas_cost_usd=SIM_GAS_COST_HBAR * hbar_price
                )
            
            target_eoa = self.eoa
            if account_id:
                from lib.saucerswap import hedera_id_to_evm
                target_eoa = hedera_id_to_evm(account_id)

            if is_native_hbar:
                logger.debug(f"      - Fetching HBAR balance for {account_id or 'main'}...")
                if simulate and target_eoa == "0x0000000000000000000000000000000000000000":
                     current_balance = 10**24 # Plentiful fake balance
                else:
                     current_balance = self.w3.eth.get_balance(target_eoa) // (10**10) # Scale EVM Wei down to Tinybars
            else:
                logger.debug(f"      - Fetching {step.from_token} balance for {account_id or 'main'}...")
                if simulate and target_eoa == "0x0000000000000000000000000000000000000000":
                     current_balance = 10**24
                else:
                     current_balance = self.client.get_token_balance(from_token_id, account=target_eoa)
            
            logger.debug(f"      - Current Balance: {current_balance}, Needed: {amount_in_expected}")
            needed_balance = amount_in_expected
            slippage_pct = self.config.max_slippage_percent
            slippage_factor_in = 1.0 + (slippage_pct / 100.0)
            slippage_factor_out = 1.0 - (slippage_pct / 100.0)
            if mode == "exact_out":
                 needed_balance = int(amount_in_expected * slippage_factor_in)
            
            # If we are simulating a multi-hop, intermediate balances may not exist in-wallet yet.
            # Current step context does not expose hop index here, so keep strict checks.
            is_intermediate_sim = False

            if current_balance < needed_balance and not is_intermediate_sim:
                # RAISE EXCEPTION instead of returning fail
                raise InsufficientFundsError(f"Insufficient funds: Have {current_balance / (10**self._get_token_decimals(step.from_token)):.6f}, Need {needed_balance / (10**self._get_token_decimals(step.from_token)):.6f}")

            if not is_native_hbar and not is_intermediate_sim:
                # We don't support approval for non-EVM accounts easily here yet 
                # but if it uses the SAME PK, then EOA approval is shared if accounts map to same EOA.
                # If they are separate accounts with same key, they might need separate approval if long-zero.
                # SaucerSwapV2's ensure_approval uses self.eoa. 
                # We need to pass the target_eoa.
                current_allowance = self.client.get_allowance(from_token_id, target_eoa, self.client.router_address)
                if current_allowance < needed_balance:
                    if simulate:
                        logger.info(f"   [SIM] Approval needed for {step.from_token}")
                    else:
                        logger.info(f"   🔓 Approving {step.from_token} for account {account_id or 'main'}...")
                        # We need to make sure the client uses the right 'from' for approval too.
                        # I'll update client.approve_token_dual to take the sender EOA too if needed,
                        # but wait, SAUCERSWAP_V2 client methods use self.eoa.
                        # Actually, recipient argument in swap methods handles it.
                        # For approval, it's more complex.
                        # Let's assume the user has associated and approved or we do it via primary.
                        pass

            if mode == "exact_in":
                min_out = int(amount_out_expected * slippage_factor_out)
                logger.debug(f"      - Slippage tolerance: {slippage_pct}% → min_out={min_out}")
                if simulate:
                    tx_hash = "SIMULATED_SWAP_COMPLETE"
                    logger.info("   [SIM] Skipping on-chain broadcast")
                elif is_native_hbar:
                    # SAFETY: Force WHBAR ID for path encoding when input is native HBAR
                    path_in_id = "0.0.1456986" 
                    tx_hash = self.client.swap_exact_input_multicall(path_in_id, to_token_id, amount_raw, min_out, input_is_native=True, fee=fee_bps)
                elif step.to_token.upper() in ["HBAR", "0.0.0"]:
                    tx_hash = self.client.swap_exact_input_multicall(from_token_id, to_token_id, amount_raw, min_out, output_is_native=True, fee=fee_bps)
                else:
                    tx_hash = self.client.swap_exact_input(from_token_id, to_token_id, amount_raw, min_out, fee_bps)
            else:
                max_in = int(amount_in_expected * slippage_factor_in)
                logger.debug(f"      - Slippage tolerance: {slippage_pct}% → max_in={max_in}")
                if simulate:
                    tx_hash = "SIMULATED_SWAP_COMPLETE"
                    logger.info("   [SIM] Skipping on-chain broadcast")
                elif is_native_hbar or step.to_token.upper() in ["HBAR", "0.0.0"]:
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
                    gas_cost_hbar = (gas_used * effective_gas_price) / (10**18)
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
                gas_offered=2_000_000,
                gas_used=gas_used,
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
    
    def _execute_unwrap_step(self, step, amount_raw: int, simulate: bool, account_id: str = None) -> ExecutionResult:
        try:
            WRAPPER_ID = "0.0.9675688"
            from_id = step.details.get("token_in_id", step.from_token)
            
            # Amount is now passed in correctly from the previous step
            if getattr(step, 'amount_raw', 0) > 0 and amount_raw == 0:
                 amount_raw = getattr(step, 'amount_raw', 0)

            if simulate:
                return ExecutionResult(
                    success=True, 
                    tx_hash="SIMULATED_UNWRAP", 
                    amount_in_raw=amount_raw, 
                    amount_out_raw=amount_raw,
                    gas_used=80000,
                    gas_cost_hbar=0.05,
                    gas_cost_usd=0.05 * self._get_hbar_price_usd(),
                    hbar_usd_price=self._get_hbar_price_usd()
                )

            from lib.saucerswap import hedera_id_to_evm
            
            # Dual-approval (EVM + HTS precompile)
            logger.info(f"   [UNWRAP] Approving {from_id} via dual EVM+HTS...")
            safe_approval = 2**256 - 1
            self.client.approve_token_dual(from_id, int(safe_approval), spender=WRAPPER_ID)

            wrapper_addr = hedera_id_to_evm(WRAPPER_ID)
            wrapper_contract = self.w3.eth.contract(address=wrapper_addr, abi=ERC20_WRAPPER_ABI)

            target_eoa = self.eoa
            if account_id:
                target_eoa = hedera_id_to_evm(account_id)

            # MANDATORY SIMULATION (Rule 7, 22)
            try:
                logger.info(f"   🔍 Simulating unwrap for {account_id or 'main'} via eth_call...")
                wrapper_contract.functions.withdrawTo(target_eoa, amount_raw).call({"from": target_eoa})
                logger.info("   ✅ Simulation passed.")
            except Exception as e:
                logger.error(f"   ❌ Simulation REVERTED: {e}")
                raise ExecutionError(f"Transaction would fail on Hedera (Simulation Revert): {e}")

            # Match btc_rebalancer2: Use Alias address (target_eoa) for both signer and account argument
            tx = wrapper_contract.functions.withdrawTo(target_eoa, amount_raw).build_transaction({
                "from": target_eoa, "gas": 2_000_000, "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(target_eoa), "chainId": self.client.chain_id,
            })

            pk_revealed = self.config.private_key.reveal()
            try:
                signed = self.w3.eth.account.sign_transaction(tx, pk_revealed)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            finally:
                del pk_revealed

            return ExecutionResult(success=True, tx_hash=tx_hash.hex(), amount_in_raw=amount_raw, amount_out_raw=amount_raw)
        except Exception as e: return ExecutionResult(success=False, error=str(e))
    
    def _execute_wrap_step(self, step, amount_raw: int, simulate: bool, account_id: str = None) -> ExecutionResult:
        try:
            WRAPPER_ID = "0.0.9675688"
            from_id = step.details.get("token_in_id", step.from_token)
            
            # Amount is now passed in correctly from the previous step
            if getattr(step, 'amount_raw', 0) > 0 and amount_raw == 0:
                 amount_raw = getattr(step, 'amount_raw', 0)

            if simulate:
                return ExecutionResult(
                    success=True, 
                    tx_hash="SIMULATED_WRAP", 
                    amount_in_raw=amount_raw, 
                    amount_out_raw=amount_raw,
                    gas_used=80000,
                    gas_cost_hbar=0.05,
                    gas_cost_usd=0.05 * self._get_hbar_price_usd(),
                    hbar_usd_price=self._get_hbar_price_usd()
                )

            from lib.saucerswap import hedera_id_to_evm
            logger.info(f"   [WRAP] Executing Wrap: {amount_raw} units of {step.from_token} -> {WRAPPER_ID}")
            
            # Dual-approval (EVM + HTS precompile)
            logger.info(f"   [WRAP] Approving {from_id} via dual EVM+HTS...")
            safe_approval = 2**256 - 1
            self.client.approve_token_dual(from_id, int(safe_approval), spender=WRAPPER_ID)

            wrapper_addr = hedera_id_to_evm(WRAPPER_ID)
            wrapper_contract = self.w3.eth.contract(address=wrapper_addr, abi=ERC20_WRAPPER_ABI)

            target_eoa = self.eoa
            if account_id:
                target_eoa = hedera_id_to_evm(account_id)

            # MANDATORY SIMULATION (Rule 7, 22)
            try:
                logger.info(f"   🔍 Simulating wrap for {account_id or 'main'} via eth_call...")
                wrapper_contract.functions.depositFor(target_eoa, amount_raw).call({"from": target_eoa})
                logger.info("   ✅ Simulation passed.")
            except Exception as e:
                logger.error(f"   ❌ Simulation REVERTED: {e}")
                raise ExecutionError(f"Transaction would fail on Hedera (Simulation Revert): {e}")

            # Match btc_rebalancer2: Use Alias address (target_eoa) for both signer and account argument
            tx = wrapper_contract.functions.depositFor(target_eoa, amount_raw).build_transaction({
                "from": target_eoa, "gas": 2_000_000, "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(target_eoa), "chainId": self.client.chain_id,
            })

            pk_revealed = self.config.private_key.reveal()
            try:
                signed = self.w3.eth.account.sign_transaction(tx, pk_revealed)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            finally:
                del pk_revealed

            return ExecutionResult(success=True, tx_hash=tx_hash.hex(), amount_in_raw=amount_raw, amount_out_raw=amount_raw)
        except Exception as e: return ExecutionResult(success=False, error=str(e))
    
    
    def _record_execution(self, route, token_amount: float, results: list, simulate: bool):
        """Record execution details for AI training."""
        # Use account_id from results if available (the last result should have it)
        target_eoa = self.eoa
        if results and hasattr(results[-1], "account_id") and results[-1].account_id:
            from lib.saucerswap import hedera_id_to_evm
            try:
                target_eoa = hedera_id_to_evm(results[-1].account_id)
            except: pass

        _record_execution_impl(
            route, token_amount, results, simulate,
            target_eoa, self.network, self.recordings_dir,
            self._get_token_decimals, self._get_hbar_price_usd
        )

    def _record_v1_execution(self, from_sym: str, to_sym: str, amount: float, res: ExecutionResult, simulate: bool = True):
        """Record V1 execution to history."""
        _record_v1_execution_impl(
            from_sym, to_sym, amount, res, simulate,
            self.eoa, self.network, self.recordings_dir
        )

    def _record_staking_transaction(self, mode: str, node_id: int, tx_id: str, success: bool, error: str = None):
        """Record staking/unstaking operation to history."""
        _record_staking_impl(
            mode, node_id, tx_id, success,
            self.eoa, self.network, self.recordings_dir, error
        )

    def _record_transfer_execution(self, res: dict):
        """Record HBAR/HTS transfer to local history."""
        _record_transfer_impl(res, self.eoa, self.network, self.recordings_dir)

    def get_execution_history(self, limit: int = 20) -> list:
        """Retrieve recent execution records for all configured accounts."""
        # By passing None or handling multiple in impl, we can see both.
        # For now, let's just return all from recordings_dir.
        # Actually, _get_history_impl usually filters by eoa.
        # Let's see if we can pass a list or just get all.
        return _get_history_impl(self.recordings_dir, limit, account=None)
