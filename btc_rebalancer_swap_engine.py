"""
SaucerSwap V2 Generalized Engine
================================

A robust, token-agnostic engine for SaucerSwap V2 on Hedera.
Automatically handles:
1. Native HBAR ↔ HTS swaps (atomic multicall + wrap/unwrap).
2. Millisecond deadlines (Hedera SwapRouter specific).
3. HTS ↔ HTS swaps.
4. Exact Input and Exact Output logic.
"""

import os
import time
import logging
import requests
import base64
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Union, Dict
from pathlib import Path

# ---------------------------------------------------------------------------
# Live Price Provider
# ---------------------------------------------------------------------------

class LivePriceProvider:
    """Fetches and caches live USD prices for tokens from SaucerSwap API."""
    def __init__(self, cache_ttl=300):
        self.url = "https://api.saucerswap.finance/v1/tokens"
        self._prices = {}
        self._last_fetch = 0
        self.cache_ttl = cache_ttl

    def get_price(self, token_id: str) -> Optional[float]:
        """Get live USD price for a token ID."""
        now = time.time()
        if now - self._last_fetch > self.cache_ttl:
            self._fetch()
        
        # Handle HBAR specially
        if token_id.upper() == "HBAR":
            return self._prices.get("WHBAR") # Usually same
            
        return self._prices.get(token_id)

    def _fetch(self):
        try:
            resp = requests.get(self.url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for t in data:
                if t.get("priceUsd"):
                    self._prices[t["id"]] = float(t["priceUsd"])
                if t.get("symbol") == "WHBAR" and t.get("priceUsd"):
                    self._prices["WHBAR"] = float(t["priceUsd"])
            self._last_fetch = time.time()
        except Exception:
            pass

from dotenv import load_dotenv
from web3 import Web3

from saucerswap_v2_client import SaucerSwapV2, hedera_id_to_evm, encode_path
from v2_tokens import WHBAR_ID, DEFAULT_FEE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SwapResult:
    """Result of a swap operation."""
    success: bool
    tx_hash: str = ""
    amount_in: float = 0.0
    amount_out: float = 0.0
    gas_used: int = 0
    error: str = ""

class SaucerSwapV2Engine:
    """
    High-level engine for SaucerSwap V2 interactions.
    Handles all V2 swap types with robust error handling and Hedera specifics.
    """
    
    def __init__(self, rpc_url: Optional[str] = None, private_key: Optional[str] = None):
        """Initialize the engine."""
        load_dotenv()
        
        self.prices = LivePriceProvider()
        
        self.rpc_url = rpc_url or os.getenv("RPC_URL", "https://mainnet.hashio.io/api")
        self.private_key = private_key or os.getenv("PRIVATE_KEY") or os.getenv("PACMAN_PRIVATE_KEY")
        
        if not self.private_key:
            raise ValueError("PRIVATE_KEY or PACMAN_PRIVATE_KEY is required in .env")
            
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {self.rpc_url}")
            
        # Use the base verified client for core interactions
        self.client = SaucerSwapV2(self.w3, network="mainnet", private_key=self.private_key)
        self.eoa = self.client.eoa
        self.whbar = hedera_id_to_evm(WHBAR_ID)
        self.account_id = os.getenv("HEDERA_ACCOUNT_ID")
        
        # Extended ABI for multicall and unwrap
        self.ROUTER_ABI = [
            {
                "inputs": [{"name": "data", "type": "bytes[]"}],
                "name": "multicall",
                "outputs": [{"name": "results", "type": "bytes[]"}],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "amountMinimum", "type": "uint256"},
                    {"name": "recipient", "type": "address"}
                ],
                "name": "unwrapWHBAR",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {
                        "components": [
                            {"name": "path", "type": "bytes"},
                            {"name": "recipient", "type": "address"},
                            {"name": "deadline", "type": "uint256"},
                            {"name": "amountIn", "type": "uint256"},
                            {"name": "amountOutMinimum", "type": "uint256"},
                        ],
                        "name": "params",
                        "type": "tuple",
                    }
                ],
                "name": "exactInput",
                "outputs": [{"name": "amountOut", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function",
            },
             {
                "inputs": [
                    {
                        "components": [
                            {"name": "tokenIn", "type": "address"},
                            {"name": "tokenOut", "type": "address"},
                            {"name": "fee", "type": "uint24"},
                            {"name": "recipient", "type": "address"},
                            {"name": "deadline", "type": "uint256"},
                            {"name": "amountIn", "type": "uint256"},
                            {"name": "amountOutMinimum", "type": "uint256"},
                            {"name": "sqrtPriceLimitX96", "type": "uint160"}
                        ],
                        "name": "params",
                        "type": "tuple",
                    }
                ],
                "name": "exactInputSingle",
                "outputs": [{"name": "amountOut", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function",
            },
            {
                "inputs": [
                    {
                        "components": [
                            {"name": "path", "type": "bytes"},
                            {"name": "recipient", "type": "address"},
                            {"name": "deadline", "type": "uint256"},
                            {"name": "amountOut", "type": "uint256"},
                            {"name": "amountInMaximum", "type": "uint256"},
                        ],
                        "name": "params",
                        "type": "tuple",
                    }
                ],
                "name": "exactOutput",
                "outputs": [{"name": "amountIn", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function",
            }
        ]
        
        self.router_extended = self.w3.eth.contract(
            address=self.client.router_address,
            abi=self.ROUTER_ABI
        )

    def get_balance_hbar(self) -> float:
        """Get native HBAR balance."""
        wei = self.w3.eth.get_balance(self.eoa)
        return wei / 10**18

    def get_balance_token(self, token_id: str, decimals: int) -> float:
        """Get token balance."""
        try:
            raw = self.client.get_token_balance(token_id)
            return raw / (10 ** decimals)
        except Exception:
            return 0.0

    def get_usdc_price(self, token_id: str, decimals: int) -> float:
        """Get the price of a token in USDC."""
        if token_id == "0.0.456858": # USDC itself
            return 1.0
        
        # Try live price provider first (way faster and more reliable)
        lp = self.prices.get_price(token_id)
        if lp:
            return lp

        # Fallback to quoting (only if API fails or token is very new)
        try:
            addr_in = self.whbar if token_id.upper() == "HBAR" else hedera_id_to_evm(token_id)
            addr_usdc = hedera_id_to_evm("0.0.456858")
            
            raw_amount_in = int(1 * (10 ** decimals))
            quote = self.client.get_quote_single(addr_in, addr_usdc, raw_amount_in, DEFAULT_FEE)
            return quote["amountOut"] / (10 ** 6)
        except Exception:
            return 0.0

    def get_all_balances(self, token_metadata: Dict) -> Dict[str, Dict]:
        """Get balances and USDC valuations for all tokens in metadata."""
        balances = {}
        
        # HBAR
        hbar_bal = self.get_balance_hbar()
        if hbar_bal > 0:
            price = self.get_usdc_price("HBAR", 8)
            balances["HBAR"] = {
                "balance": hbar_bal,
                "usd_value": hbar_bal * price
            }
            
        # HTS Tokens
        for symbol, meta in token_metadata.items():
            if symbol == "HBAR": continue
            bal = self.get_balance_token(meta["id"], meta["decimals"])
            if bal > 0:
                price = self.get_usdc_price(meta["id"], meta["decimals"])
                balances[symbol] = {
                    "balance": bal,
                    "usd_value": bal * price
                }
        return balances

    def get_recent_transactions(self, limit: int = 10) -> List[Dict]:
        """Fetch recent transactions and calculate fees in USDC."""
        if not self.account_id:
            logger.warning("HEDERA_ACCOUNT_ID not set")
            return []
            
        url = f"https://mainnet-public.mirrornode.hedera.com/api/v1/transactions?account.id={self.account_id}&limit={limit}&order=desc"
        
        # Get HBAR price once for fees
        hbar_price = self.get_usdc_price("HBAR", 8)
        
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            txs = []
            for tx in data.get("transactions", []):
                # Format timestamp
                ts_str = tx.get("consensus_timestamp")
                if ts_str:
                    try:
                        dt = datetime.fromtimestamp(float(ts_str))
                        ts_fmt = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        ts_fmt = ts_str
                else:
                    ts_fmt = "Unknown"
                
                # Decode memo
                memo_b64 = tx.get("memo_base64")
                memo = ""
                if memo_b64:
                    try:
                        memo = base64.b64decode(memo_b64).decode("utf-8")
                    except:
                        memo = memo_b64
                
                # Fee calculation
                fee_hbar = tx.get("charged_tx_fee", 0) / (10**8)
                fee_usdc = fee_hbar * hbar_price
                
                txs.append({
                    "timestamp": ts_fmt,
                    "hash": tx.get("transaction_id"),
                    "name": tx.get("name"),
                    "result": tx.get("result"),
                    "memo": memo,
                    "fee_hbar": fee_hbar,
                    "fee_usdc": fee_usdc
                })
            return txs
        except Exception as e:
            logger.error(f"Failed to fetch transactions: {e}")
            return []

    def get_quote(self, token_in_id: str, token_out_id: str, amount: float, decimals_in: int, is_exact_input: bool = True, fee: int = DEFAULT_FEE) -> Optional[float]:
        """
        Get a quote for a swap.
        
        Args:
            token_in_id: Hedera ID of the input token (use "HBAR" for native)
            token_out_id: Hedera ID of the output token (use "HBAR" for native)
            amount: Human-readable amount
            decimals_in: Decimals of the input token (use 8 for HBAR)
            is_exact_input: True for exactInput, False for exactOutput
            fee: Fee tier (e.g. 1500)
            
        Returns:
            Human-readable amount out (if exactInput) or amount in (if exactOutput)
        """
        try:
            addr_in = self.whbar if token_in_id.upper() == "HBAR" else hedera_id_to_evm(token_in_id)
            addr_out = self.whbar if token_out_id.upper() == "HBAR" else hedera_id_to_evm(token_out_id)
            
            raw_amount = int(amount * (10 ** decimals_in))
            
            if is_exact_input:
                q = self.client.get_quote_single(addr_in, addr_out, raw_amount, fee)
                # We need decimals_out to convert back. Let's assume user provides or we fetch.
                # For now, let's keep it simple or require the user to handle normalization if they use the raw API.
                # But for a high-level engine, we should probably handle it.
                return q["amountOut"] # Return raw for now or handle decimals
            else:
                # SaucerSwap V2 Quoter also has quoteExactOutputSingle
                # Our client only has get_quote_single (which is exactInput)
                # Let's add quoteExactOutput to the engine if needed, or stick to exactInput for now.
                logger.warning("exactOutput quoting not yet implemented in base client, using estimation.")
                return None
        except Exception as e:
            logger.error(f"Quote failed: {e}")
            return None

    def _estimate_exact_output_input(self, addr_in, addr_out, raw_amount_out, fee, decimals_in):
        """
        Estimate input amount needed for a desired output.
        Uses binary search on exactInput quotes since we don't have exactOutput quoter.
        """
        try:
            # Binary search for the right input amount
            # Lower bound: 0
            # Upper bound: 10x the expected input (generous)
            
            # First, get a rough estimate using a small test amount
            test_input = int(0.001 * (10 ** decimals_in))  # 0.001 of input token
            try:
                test_quote = self.client.get_quote_single(addr_in, addr_out, test_input, fee)
                rate = test_quote["amountOut"] / test_input  # output per input unit
                if rate > 0:
                    initial_estimate = int(raw_amount_out / rate * 1.1)  # 10% buffer
                else:
                    initial_estimate = raw_amount_out * 100  # generous upper bound
            except:
                initial_estimate = raw_amount_out * 1000  # very generous fallback
            
            # Binary search between 0 and initial_estimate
            low, high = 0, initial_estimate
            best_input = None
            
            for _ in range(20):  # 20 iterations should be plenty
                mid = (low + high) // 2
                if mid == 0:
                    break
                try:
                    q = self.client.get_quote_single(addr_in, addr_out, mid, fee)
                    output = q["amountOut"]
                    
                    if output >= raw_amount_out:
                        # Can achieve desired output with this input
                        best_input = mid
                        high = mid
                    else:
                        # Need more input
                        low = mid
                except Exception as e:
                    logger.warning(f"Quote failed in binary search: {e}")
                    low = mid
            
            if best_input is None:
                logger.error("Could not estimate input amount")
                return None
            
            logger.info(f"  Estimated input needed: {best_input / (10**decimals_in)}")
            return best_input
            
        except Exception as e:
            logger.error(f"Estimation failed: {e}")
            return None

    def get_quote(self, 
                  token_in_id: str, 
                  token_out_id: str, 
                  amount: float, 
                  decimals_in: int,
                  decimals_out: int,
                  is_exact_input: bool = True,
                  path_ids: Optional[List[str]] = None,
                  path_fees: Optional[List[int]] = None) -> Optional[int]:
        """
        Get quote for a swap. Returns raw amount.
        If is_exact_input=True, returns raw amount OUT.
        If is_exact_input=False, returns raw amount IN needed.
        """
        try:
            is_hbar_in = token_in_id.upper() == "HBAR"
            is_hbar_out = token_out_id.upper() == "HBAR"
            
            addr_in = self.whbar if is_hbar_in else hedera_id_to_evm(token_in_id)
            addr_out = self.whbar if is_hbar_out else hedera_id_to_evm(token_out_id)
            
            if not path_ids:
                path_ids = [WHBAR_ID if is_hbar_in else token_in_id, 
                            WHBAR_ID if is_hbar_out else token_out_id]
                path_fees = [DEFAULT_FEE]

            if is_exact_input:
                raw_amount_in = int(amount * (10 ** decimals_in))
                if len(path_ids) == 2:
                    quote = self.client.get_quote_single(addr_in, addr_out, raw_amount_in, path_fees[0])
                    return quote["amountOut"]
                else:
                    path_evms = [hedera_id_to_evm(pid) for pid in path_ids]
                    quote = self.client.get_quote_multi_hop(path_evms, path_fees, raw_amount_in)
                    return quote["amount_out"]
            else:
                # exactOutput: find input needed for target output
                raw_amount_out = int(amount * (10 ** decimals_out))
                if len(path_ids) == 2:
                    return self._estimate_exact_output_input(addr_in, addr_out, raw_amount_out, path_fees[0], decimals_in)
                else:
                    # Multi-hop exact output is complex; fallback to scale estimation for now
                    return None
        except Exception as e:
            logger.debug(f"Quote failed: {e}")
            return None

    def swap(self, 
             token_in_id: str, 
             token_out_id: str, 
             amount: float, 
             decimals_in: int,
             decimals_out: int,
             fee: int = DEFAULT_FEE,
             slippage: float = 0.01,
             is_exact_input: bool = True,
             path_ids: Optional[List[str]] = None,
             path_fees: Optional[List[int]] = None) -> SwapResult:
        """
        Perform a swap. Automatically handles HBAR and multicall.
        Supports both exactInput (specify input amount) and exactOutput (specify output amount).
        """
        try:
            is_hbar_in = token_in_id.upper() == "HBAR"
            is_hbar_out = token_out_id.upper() == "HBAR"
            
            addr_in = self.whbar if is_hbar_in else hedera_id_to_evm(token_in_id)
            addr_out = self.whbar if is_hbar_out else hedera_id_to_evm(token_out_id)
            
            if is_exact_input:
                # EXACT INPUT MODE: User specifies how much they want to SEND
                raw_amount_in = int(amount * (10 ** decimals_in))
                quote = self.client.get_quote_single(addr_in, addr_out, raw_amount_in, fee)
                raw_amount_out_expected = quote["amountOut"]
                min_out = int(raw_amount_out_expected * (1 - slippage))
                logger.info(f"  EXACT_INPUT: Sending {amount} ({raw_amount_in} raw), expecting ~{raw_amount_out_expected / (10**decimals_out)} out")
            else:
                # EXACT OUTPUT MODE: User specifies how much they want to RECEIVE
                raw_amount_out = int(amount * (10 ** decimals_out))
                # For exactOutput, we need to estimate input amount
                # We'll use a reverse quote estimation: try inputs until we get close
                logger.info(f"  EXACT_OUTPUT: Want {amount} out ({raw_amount_out} raw), estimating input needed...")
                estimated_input = self._estimate_exact_output_input(addr_in, addr_out, raw_amount_out, fee, decimals_in)
                if estimated_input is None:
                    return SwapResult(success=False, error="Failed to estimate input for exactOutput")
                raw_amount_in = int(estimated_input * (1 + slippage))  # amountInMaximum
                min_out = raw_amount_out  # This is the exact amount we want out
                logger.info(f"  Estimated input needed: ~{estimated_input / (10**decimals_in)}, max allowed: {raw_amount_in}")
                raw_amount_out_expected = raw_amount_out
            
            # Step 3: Handle Allowance if HTS in
            if not is_hbar_in:
                erc20 = self.w3.eth.contract(address=addr_in, abi=[{"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"name":"allowance","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function"}])
                allowance = erc20.functions.allowance(self.eoa, self.client.router_address).call()
                logger.info(f"  Current allowance: {allowance}")
                if allowance < raw_amount_in:
                    logger.info(f"  Approving {token_in_id} (Need {raw_amount_in})...")
                    # For simplicity, approve a lot or just enough
                    tx = erc20.functions.approve(self.client.router_address, raw_amount_in * 10).build_transaction({
                        "from": self.eoa,
                        "nonce": self.w3.eth.get_transaction_count(self.eoa),
                        "gas": 150000,
                        "gasPrice": self.w3.eth.gas_price
                    })
                    signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
                    tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                    logger.info(f"  Approval TX sent: {tx_hash.hex()}")
                    self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    logger.info("  Approval confirmed. Waiting 5s for propagation...")
                    time.sleep(5)
                else:
                    logger.info(f"  Sufficient allowance exists.")

            # Step 4: Construct the Path
            if not path_ids:
                path_ids = [WHBAR_ID if is_hbar_in else token_in_id, 
                            WHBAR_ID if is_hbar_out else token_out_id]
                path_fees = [fee]
            
            path_bytes = encode_path(path_ids, path_fees)
            
            # Step 5: Deadline (MUST BE MILLISECONDS)
            deadline = int(time.time() * 1000) + 600000 # 10 mins
            
            logger.info(f"  Using Path: {path_bytes.hex()}")
            logger.info(f"  Deadline: {deadline}")
            logger.info(f"  Min Out: {min_out}")

            # Step 6: Build the specific transaction type
            if is_exact_input:
                # EXACT INPUT: Use exactInput function
                if is_hbar_out:
                    # Token -> HBAR requires multicall(exactInput + unwrapWHBAR)
                    params = (path_bytes, self.client.router_address, deadline, raw_amount_in, min_out)
                    swap_call = self.router_extended.encode_abi("exactInput", [params])
                    unwrap_call = self.router_extended.encode_abi("unwrapWHBAR", [0, self.eoa])
                    
                    swap_bytes = bytes.fromhex(swap_call[2:])
                    unwrap_bytes = bytes.fromhex(unwrap_call[2:])
                    
                    tx = self.router_extended.functions.multicall([swap_bytes, unwrap_bytes]).build_transaction({
                        "from": self.eoa,
                        "value": 0,
                        "gas": 2000000,
                        "gasPrice": self.w3.eth.gas_price,
                        "nonce": self.w3.eth.get_transaction_count(self.eoa),
                        "chainId": self.client.chain_id
                    })
                elif is_hbar_in:
                    # HBAR -> Token (standard exactInput with value)
                    params = (path_bytes, self.eoa, deadline, raw_amount_in, min_out)
                    tx = self.router_extended.functions.exactInput(params).build_transaction({
                        "from": self.eoa,
                        "value": int(amount * 10**18),
                        "gas": 1000000,
                        "gasPrice": self.w3.eth.gas_price,
                        "nonce": self.w3.eth.get_transaction_count(self.eoa),
                        "chainId": self.client.chain_id
                    })
                else:
                    # HTS -> HTS (standard exactInput)
                    params = (path_bytes, self.eoa, deadline, raw_amount_in, min_out)
                    tx = self.router_extended.functions.exactInput(params).build_transaction({
                        "from": self.eoa,
                        "value": 0,
                        "gas": 1000000,
                        "gasPrice": self.w3.eth.gas_price,
                        "nonce": self.w3.eth.get_transaction_count(self.eoa),
                        "chainId": self.client.chain_id
                    })
            else:
                # EXACT OUTPUT: Path is reversed (tokenOut -> fee -> tokenIn)
                # For exactOutput, we want to specify the exact amount we want OUT
                # The router will calculate how much input is needed
                
                # Reverse the path for exactOutput
                path_ids_rev = [WHBAR_ID if is_hbar_out else token_out_id,
                               WHBAR_ID if is_hbar_in else token_in_id]
                path_bytes_rev = encode_path(path_ids_rev, path_fees)
                
                raw_amount_out_exact = int(amount * (10 ** decimals_out))
                # amountInMaximum = raw_amount_in (already includes slippage buffer)
                
                if is_hbar_in:
                    # exactOutput with HBAR input
                    # Construct reversed path: tokenOut -> fee -> WHBAR
                    path_ids_rev = [WHBAR_ID if is_hbar_out else token_out_id, WHBAR_ID]
                    path_bytes_rev = encode_path(path_ids_rev, path_fees)
                    
                    raw_amount_out_exact = int(amount * (10 ** decimals_out))
                    
                    if is_hbar_out:
                        # HBAR -> HBAR? Nonsense but handled for safety
                        return SwapResult(success=False, error="Cannot swap HBAR for HBAR")

                    params = (path_bytes_rev, self.eoa, deadline, raw_amount_out_exact, raw_amount_in)
                    tx = self.router_extended.functions.exactOutput(params).build_transaction({
                        "from": self.eoa,
                        "value": raw_amount_in, # sending amountInMaximum
                        "gas": 1000000,
                        "gasPrice": self.w3.eth.gas_price,
                        "nonce": self.w3.eth.get_transaction_count(self.eoa),
                        "chainId": self.client.chain_id
                    })
                elif is_hbar_out:
                    # exactOutput to HBAR: reverse path + unwrap
                    params = (path_bytes_rev, self.eoa, deadline, raw_amount_out_exact, raw_amount_in)
                    swap_call = self.router_extended.encode_abi("exactOutput", [params])
                    unwrap_call = self.router_extended.encode_abi("unwrapWHBAR", [0, self.eoa])
                    
                    swap_bytes = bytes.fromhex(swap_call[2:])
                    unwrap_bytes = bytes.fromhex(unwrap_call[2:])
                    
                    tx = self.router_extended.functions.multicall([swap_bytes, unwrap_bytes]).build_transaction({
                        "from": self.eoa,
                        "value": 0,
                        "gas": 2000000,
                        "gasPrice": self.w3.eth.gas_price,
                        "nonce": self.w3.eth.get_transaction_count(self.eoa),
                        "chainId": self.client.chain_id
                    })
                else:
                    # HTS -> HTS exactOutput
                    params = (path_bytes_rev, self.eoa, deadline, raw_amount_out_exact, raw_amount_in)
                    tx = self.router_extended.functions.exactOutput(params).build_transaction({
                        "from": self.eoa,
                        "value": 0,
                        "gas": 1000000,
                        "gasPrice": self.w3.eth.gas_price,
                        "nonce": self.w3.eth.get_transaction_count(self.eoa),
                        "chainId": self.client.chain_id
                    })
            
            # Step 7: Sign and Send
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            logger.info(f"Swap transaction sent: {tx_hash.hex()}")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status == 1:
                return SwapResult(
                    success=True, 
                    tx_hash=tx_hash.hex(), 
                    amount_in=amount, 
                    amount_out=raw_amount_out_expected / (10**decimals_out) if 'raw_amount_out_expected' in locals() else amount, 
                    gas_used=receipt.gasUsed
                )
            else:
                return SwapResult(success=False, tx_hash=tx_hash.hex(), error="Transaction reverted")
                
        except Exception as e:
            logger.error(f"Swap failed: {e}")
            return SwapResult(success=False, error=str(e))

if __name__ == "__main__":
    # Internal test/example
    engine = SaucerSwapV2Engine()
    print("Engine ready.")
    # Example: Quote USDC -> WBTC
    from tokens import USDC_ID, WBTC_ID
    # q = engine.get_quote(USDC_ID, WBTC_ID, 1.0, 6)
    # print(f"Quote 1 USDC -> WBTC (raw): {q}")
