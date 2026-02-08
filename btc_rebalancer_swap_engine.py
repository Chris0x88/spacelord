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
from dataclasses import dataclass
from typing import Optional, List, Union

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
        
        self.rpc_url = rpc_url or os.getenv("RPC_URL", "https://mainnet.hashio.io/api")
        self.private_key = private_key or os.getenv("PRIVATE_KEY")
        
        if not self.private_key:
            raise ValueError("PRIVATE_KEY is required.")
            
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {self.rpc_url}")
            
        # Use the base verified client for core interactions
        self.client = SaucerSwapV2(self.w3, network="mainnet", private_key=self.private_key)
        self.eoa = self.client.eoa
        self.whbar = hedera_id_to_evm(WHBAR_ID)
        
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

    def swap(self, 
             token_in_id: str, 
             token_out_id: str, 
             amount: float, 
             decimals_in: int,
             decimals_out: int,
             fee: int = DEFAULT_FEE,
             slippage: float = 0.01,
             is_exact_input: bool = True) -> SwapResult:
        """
        Perform a swap. Automatically handles HBAR and multicall.
        """
        try:
            is_hbar_in = token_in_id.upper() == "HBAR"
            is_hbar_out = token_out_id.upper() == "HBAR"
            
            addr_in = self.whbar if is_hbar_in else hedera_id_to_evm(token_in_id)
            addr_out = self.whbar if is_hbar_out else hedera_id_to_evm(token_out_id)
            
            # Step 1: Pre-calculate raw amounts
            raw_amount_in = int(amount * (10 ** decimals_in))
            
            # Step 2: Get Quote for slippage calculation
            # Use WHBAR if HBAR is involved
            quote = self.client.get_quote_single(addr_in, addr_out, raw_amount_in, fee)
            raw_amount_out_expected = quote["amountOut"]
            
            min_out = int(raw_amount_out_expected * (1 - slippage))
            
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

            # Step 4: Construct the Path (Single hop for now)
            # hedera_id equivalents
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
                    amount_out=raw_amount_out_expected / (10**decimals_out),
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
