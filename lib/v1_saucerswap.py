"""
SaucerSwap V1 (Uniswap V2) Client
=================================

A strictly decoupled connector for legacy V1 pools.
Separation ensures that V2 remains independent and unaffected.
"""

import time
import json
from pathlib import Path
from typing import List, Optional

# V1 Router: SaucerSwapV1RouterV3
V1_ROUTER_ID = "0.0.3045981"
V1_WHBAR_ID = "0.0.1456986"

# Load ABI
ABI_DIR = Path(__file__).parent.parent / "abi"
V1_ROUTER_ABI = json.loads((ABI_DIR / "v1_router.json").read_text())
ERC20_ABI = json.loads((ABI_DIR / "erc20.json").read_text())

def hedera_id_to_evm(hedera_id: str) -> str:
    from web3 import Web3
    if hedera_id.startswith("0x"):
        return Web3.to_checksum_address(hedera_id)
    parts = hedera_id.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid Hedera ID: {hedera_id}")
    num = int(parts[2])
    return Web3.to_checksum_address(f"0x{num:040x}")

class SaucerSwapV1:
    def __init__(self, w3, network: str = "mainnet", private_key: str | None = None):
        self.w3 = w3
        self.network = network
        self.private_key = private_key
        
        if private_key:
            self.account = w3.eth.account.from_key(private_key)
            self.eoa = self.account.address
        else:
            self.account = None
            self.eoa = None

        self.router_address = hedera_id_to_evm(V1_ROUTER_ID)
        self.router = w3.eth.contract(address=self.router_address, abi=V1_ROUTER_ABI)
        self.chain_id = 295 if network == "mainnet" else 296

    def _resolve_path(self, from_id: str, to_id: str) -> List[str]:
        """Convert IDs to EVM addresses, substituting WHBAR for 0.0.0."""
        id_in = V1_WHBAR_ID if (from_id == "0.0.0" or from_id.upper() == "HBAR") else from_id
        id_out = V1_WHBAR_ID if (to_id == "0.0.0" or to_id.upper() == "HBAR") else to_id
        return [hedera_id_to_evm(id_in), hedera_id_to_evm(id_out)]

    def get_quote_single(self, token_in: str, token_out: str, amount_in: int) -> int:
        """Get quote using getAmountsOut."""
        path = self._resolve_path(token_in, token_out)
        try:
            amounts = self.router.functions.getAmountsOut(amount_in, path).call()
            return amounts[-1]
        except Exception as e:
            raise RuntimeError(f"V1 Quote failed: {e}")

    def swap_exact_input(self, token_in: str, token_out: str, amount_in: int, min_amount_out: int) -> str:
        """Execute swapExactTokensForTokens."""
        if not self.private_key:
            raise ValueError("Private key required for swap")

        deadline = int(time.time()) + 600
        path = self._resolve_path(token_in, token_out)

        # Check for Native HBAR swaps (V1 uses different functions for HBAR)
        is_hbar_in = (token_in == "0.0.0" or token_in.upper() == "HBAR")
        is_hbar_out = (token_out == "0.0.0" or token_out.upper() == "HBAR")

        if is_hbar_in:
            tx_func = self.router.functions.swapExactETHForTokens(
                min_amount_out,
                path,
                self.eoa,
                deadline
            )
            value = amount_in
        elif is_hbar_out:
            tx_func = self.router.functions.swapExactTokensForETH(
                amount_in,
                min_amount_out,
                path,
                self.eoa,
                deadline
            )
            value = 0
        else:
            tx_func = self.router.functions.swapExactTokensForTokens(
                amount_in,
                min_amount_out,
                path,
                self.eoa,
                deadline
            )
            value = 0

        # Build & Sign
        tx = tx_func.build_transaction({
            "from": self.eoa,
            "gas": 1_000_000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.eoa),
            "chainId": self.chain_id,
            "value": value * 10**10 if value > 0 and is_hbar_in else 0 # native value handling
        })

        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()
